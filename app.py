import streamlit as st
import sqlite3
from datetime import datetime
import pandas as pd
import io

# 1. إعداد وتأصيل قاعدة البيانات
def init_db():
    conn = sqlite3.connect('warehouse.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS items_v3 (
            item_name TEXT NOT NULL,
            category TEXT NOT NULL,
            size TEXT NOT NULL,
            current_stock INTEGER DEFAULT 0,
            purchase_price REAL DEFAULT 0.0,
            PRIMARY KEY (item_name, size)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions_v3 (
            trans_id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_name TEXT,
            size TEXT,
            type TEXT,
            quantity INTEGER,
            employee_name TEXT,
            timestamp TEXT,
            source TEXT,
            car_number TEXT,
            notes TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS audits_v3 (
            audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_name TEXT,
            size TEXT,
            audit_date TEXT,
            system_qty INTEGER,
            physical_qty INTEGER,
            status TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users_v3 (
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL,
            role TEXT NOT NULL
        )
    ''')
    
    cursor.execute("SELECT COUNT(*) FROM users_v3")
    if cursor.fetchone() == 0:
        default_users = [
            ('عبيده', '5678', 'Worker'),
            ('المدير', '1234', 'Admin')
        ]
        cursor.executemany("INSERT INTO users_v3 VALUES (?, ?, ?)", default_users)
        conn.commit()

    cursor.execute("SELECT COUNT(*) FROM items_v3")
    if cursor.fetchone() == 0:
        sample_items = [
            ('إطار هانكوك كوريا', 'كوشوك', '205/55R16', 100, 45.0),
            ('بواجي تويوتا أصلي', 'قطع غيار', '90919-01253', 50, 5.0)
        ]
        cursor.executemany("INSERT INTO items_v3 VALUES (?, ?, ?, ?, ?)", sample_items)
        conn.commit()
        
    return conn

# إعداد الصفحة وتثبيت الـ RTL والتنسيقات البصرية
st.set_page_config(page_title="نظام إدارة المستودع", layout="wide")

st.markdown("""
    <style>
    body, div, p, span, h1, h2, h3, h4, h5, h6, label, input, select, textarea {
        direction: RTL !important;
        text-align: right !important;
        font-size: 17px !important;
    }
    .stTabs, .stSelectbox, .stRadio, .stForm {
        direction: RTL !important;
        text-align: right !important;
    }
    .stSidebar {
        direction: RTL !important;
    }
    .dataframe th {
        background-color: #1b5e20 !important;
        color: white !important;
        text-align: center !important;
        font-size: 17px !important;
    }
    .dataframe td {
        text-align: center !important;
        font-size: 16px !important;
    }
    .stForm {
        max-width: 600px !important;
        margin: 0 auto !important;
        padding: 20px !important;
        border-radius: 10px !important;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("📦 نظام إدارة مستودع القطع والكوشوك")

conn = init_db()
cursor = conn.cursor()

if "is_logged_in" not in st.session_state:
    st.session_state["is_logged_in"] = False
    st.session_state["logged_user"] = ""
    st.session_state["logged_role"] = "زائر"
    st.session_state["show_welcome"] = False

# شاشة تسجيل الدخول
if not st.session_state["is_logged_in"]:
    st.sidebar.subheader("🔒 تسجيل الدخول للنظام")
    u_input = st.sidebar.text_input("اسم المستخدم:", key="u_login")
    p_input = st.sidebar.text_input("كلمة المرور:", type="password", key="p_login")
    login_btn = st.sidebar.button("دخول")
    
    if login_btn:
        if u_input == "المدير" and p_input == "1234":
            st.session_state["is_logged_in"] = True
            st.session_state["logged_user"] = "المدير"
            st.session_state["logged_role"] = "Admin"
            st.session_state["show_welcome"] = True
            st.rerun()
        elif u_input == "عبيده" and p_input == "5678":
            st.session_state["is_logged_in"] = True
            st.session_state["logged_user"] = "عبيده"
            st.session_state["logged_role"] = "Worker"
            st.session_state["show_welcome"] = True
            st.rerun()
        elif u_input and p_input:
            cursor.execute("SELECT role FROM users_v3 WHERE username = ? AND password = ?", (u_input, p_input))
            res = cursor.fetchone()
            if res:
                st.session_state["is_logged_in"] = True
                st.session_state["logged_user"] = u_input
                st.session_state["logged_role"] = res[0]
                st.session_state["show_welcome"] = True
                st.rerun()
            else:
                st.sidebar.error("❌ بيانات الدخول غير صحيحة.")
else:
    if st.session_state["show_welcome"]:
        st.toast(f"🟢 أهلاً وسهلاً بك في النظام يا {st.session_state['logged_user']}", icon="👋")
        st.session_state["show_welcome"] = False

    st.sidebar.subheader(f"👤 المستخدم الحالي: {st.session_state['logged_user']}")
    logout_btn = st.sidebar.button("🚪 تسجيل الخروج")
    if logout_btn:
        st.toast("🔴 مع السلامة، نتمنى لك يوماً سعيداً", icon="👋")
        st.session_state["is_logged_in"] = False
        st.session_state["logged_user"] = ""
        st.session_state["logged_role"] = "زائر"
        st.rerun()

# ----------------------------------------------------
# واجهة الموظف
# ----------------------------------------------------
if st.session_state["is_logged_in"] and st.session_state["logged_role"] == "Worker":
    st.header(f"📥 تسجيل حركة مخزنية - الموظف {st.session_state['logged_user']}")
    
    cursor.execute("SELECT item_name, size FROM items_v3")
    db_items = cursor.fetchall()
    
    if not db_items:
        st.warning("لا توجد أصناف في المستودع حالياً.")
    else:
        items_list = {f"{r[0]} | المقاس: {r[1]}": (r[0], r[1]) for r in db_items}
        
        tab_in, tab_out = st.tabs(["🟢 تسجيل حركة دخول", "🔴 تسجيل حركة خروج"])
        
        with tab_in:
            st.subheader("إدخال بضاعة للمستودع")
            with st.form("form_in_small", clear_on_submit=True):
                selected_item = st.selectbox("الصنف والمقاس:", list(items_list.keys()), key="in_small_select")
                qty = st.number_input("الكمية الواردة:", min_value=1, step=1, key="in_small_qty")
                source_input = st.text_input("المصدر (المورد):", key="in_small_source")
                notes_input = st.text_area("ملاحظات:", key="in_small_notes")
                submit_in = st.form_submit_button("تأكيد الإدخال")
                
                if submit_in:
                    item_name, size = items_list[selected_item]
                    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    cursor.execute("INSERT INTO transactions_v3 (item_name, size, type, quantity, employee_name, timestamp, source, notes) VALUES (?, ?, 'دخول', ?, ?, ?, ?, ?)", (item_name, size, qty, st.session_state['logged_user'], now, source_input, notes_input))
                    cursor.execute("UPDATE items_v3 SET current_stock = current_stock + ? WHERE item_name = ? AND size = ?", (qty, item_name, size))
                    conn.commit()
                    
                    st.success(f"🟢 تم قبول المادة بنجاح! تم تسجيل إدخال {qty} قطع من الصنف '{item_name}'.")
                    st.rerun()

        with tab_out:
            st.subheader("إخراج بضاعة من المستودع")
            with st.form("form_out_small", clear_on_submit=True):
                selected_item = st.selectbox("الصنف والمقاس:", list(items_list.keys()), key="out_small_select")
                qty = st.number_input("الكمية الصادرة:", min_value=1, step=1, key="out_small_qty")
                car_input = st.text_input("رقم السيارة المستلمة:", key="out_small_car")
                notes_out = st.text_area("ملاحظات:", key="out_small_notes")
                submit_out = st.form_submit_button("تأكيد الإخراج")
                
                if submit_out:
                    item_name, size = items_list[selected_item]
                    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    cursor.execute("SELECT current_stock FROM items_v3 WHERE item_name = ? AND size = ?", (item_name, size))
                    current = cursor.fetchone()
                    
                    if current and qty > current[0]:
                        st.error(f"⚠️ خطأ: الكمية المطلوبة ({qty}) أكبر من المتوفر بالمستودع ({current[0]}).")
                    else:
                        cursor.execute("INSERT INTO transactions_v3 (item_name, size, type, quantity, employee_name, timestamp, car_number, notes) VALUES (?, ?, 'خروج', ?, ?, ?, ?, ?)", (item_name, size, qty, st.session_state['logged_user'], now, car_input, notes_out))
                        cursor.execute("UPDATE items_v3 SET current_stock = current_stock - ? WHERE item_name = ? AND size = ?", (qty, item_name, size))
                        conn.commit()
                        
                        st.success(f"🔴 تم قبول المادة بنجاح! تم تسجيل صرف {qty} قطع من الصنف '{item_name}' برقم سيارة {car_input}.")
                        st.rerun()

# ----------------------------------------------------
# واجهة الإدارة
# ----------------------------------------------------
elif st.session_state["is_logged_in"] and st.session_state["logged_role"] == "Admin":
    st.header(f"📊 لوحة تحكم الإدارة - {st.session_state['logged_user']}")
    
    # تصحيح ضرب القيم المالية بالإشارة إلى الفهارس الصحيحة
    cursor.execute("SELECT current_stock, purchase_price FROM items_v3")
    stock_rows = cursor.fetchall()
    total_inventory_value = sum([r[0] * r[1] for r in stock_rows]) if stock_rows else 0.0
    
    cursor.execute("""
        SELECT t.quantity, i.purchase_price 
        FROM transactions_v3 t 
        JOIN items_v3 i ON t.item_name = i.item_name AND t.size = i.size 
        WHERE t.type = 'خروج'
    """)
    sales_rows = cursor.fetchall()
    total_cost_sold = sum([r[0] * r[1] for r in sales_rows]) if sales_rows else 0.0
    
    col_stat1, col_stat2 = st.columns(2)
    col_stat1.metric("💰 إجمالي قيمة المخزون الحالي", f"{total_inventory_value:,.2f} دينار")
    col_stat2.metric("📋 إجمالي قيمة الصادر المستهلك", f"{total_cost_sold:,.2f} دينار")
    
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📋 كشف المخزون", "🕒 كشف الحساب التراكمي", "⚙️ إدارة الأصناف", "🟢 شاشة المطابقة", "👥 إدارة المستخدمين"])
    
    with tab1:
        st.subheader("كشف كميات المخزون المتوفرة والقيم المالية")
        cursor.execute("SELECT item_name, category, size, current_stock, purchase_price FROM items_v3")
        stock_data = cursor.fetchall()
        if stock_data:
            df_stock = pd.DataFrame(stock_data, columns=["اسم الصنف", "التصنيف", "المقاس", "الكمية المتوفرة", "سعر الشراء (دينار)"])
            df_stock["قيمة المخزون الكلية"] = df_stock["الكمية المتوفرة"] * df_stock["سعر الشراء (دينار)"]
            
            df_stock.index = range(1, len(df_stock) + 1)
            df_stock.index.name = "ت"
            
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df_stock.to_excel(writer, sheet_name='المخزون')
            excel_data = output.getvalue()
            
            st.download_button(
                label="📥 تحميل كشف المخزون بصيغة Excel",
                data=excel_data,
                file_name=f'كشف_المخزون_{datetime.now().strftime("%Y-%m-%d")}.xlsx',
                mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            
            st.dataframe(df_stock, use_container_width=True)
        else:
            st.info("المستودع فارغ حالياً.")
            
    with tab2:
        st.subheader("كشف حساب المادة التراكمي")
        cursor.execute("SELECT DISTINCT item_name, size FROM items_v3")
        mats = [f"{r[0]} | المقاس: {r[1]}" for r in cursor.fetchall()]
        
        if mats:
            selected_mat = st.selectbox("اختر المادة:", mats)
            mat_parts = selected_mat.split(" | المقاس: ")
            mat_name = mat_parts[0]
            mat_size = mat_parts[1]
            
            cursor.execute("SELECT purchase_price FROM items_v3 WHERE item_name = ? AND size = ?", (mat_name, mat_size))
            prices = cursor.fetchone()
            p_price = prices[0] if prices else 0.0
            
            cursor.execute("""
                SELECT timestamp, type, quantity, employee_name, source, car_number, notes 
                FROM transactions_v3 
                WHERE item_name = ? AND size = ? 
                ORDER BY trans_id ASC
            """, (mat_name, mat_size))
            trans_data = cursor.fetchall()
            
            if trans_data:
                account_entries = []
                running_balance = 0
                
                for r in trans_data:
                    timestamp, trans_type, qty, emp, src, car, notes = r
                    if trans_type == "دخول":
                        running_balance += qty
                        in_qty = qty
                        out_qty = 0
                    else:
                        running_balance -= qty
                        in_qty = 0
                        out_qty = qty
                        
                    financial_value = qty * p_price
                        
                    account_entries.append({
                        "التاريخ والوقت": timestamp,
                        "نوع الحركة": trans_type,
                        "عدد الدخول (الوارد)": in_qty if in_qty > 0 else 0,
                        "عدد الخروج (الصادر)": out_qty if out_qty > 0 else 0,
                        "الرصيد التراكمي": running_balance,
                        "التكلفة للحركة (دينار)": f"{financial_value:,.2f}"
                    })
                
                df_account = pd.DataFrame(account_entries)
                df_account = df_account.iloc[::-1]
                df_account.index = range(1, len(df_account) + 1)
                df_account.index.name = "ت"
                
                output_acc = io.BytesIO()
                with pd.ExcelWriter(output_acc, engine='xlsxwriter') as writer:
                    df_account.to_excel(writer, sheet_name='كشف الحركات')
                excel_acc = output_acc.getvalue()
                
                st.download_button(
                    label="📥 تحميل كشف الحساب بصيغة Excel",
                    data=excel_acc,
                    file_name=f'كشف_حساب_{mat_name}.xlsx',
                    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                )
                
                def color_type(val):
                    if val == 'دخول': return 'background-color: #C8E6C9; font-weight: bold;'
                    elif val == 'خروج': return 'background-color: #FFCDD2; font-weight: bold;'
                    return ''
                
                st.dataframe(df_account.style.map(color_type, subset=['نوع الحركة']), use_container_width=True)
                st.markdown(f"**💰 التكلفة الإجمالية لهذه المادة بالمستودع حالياً:** {running_balance * p_price:,.2f} دينار")
            else:
                st.info("لم يتم العثور على أي حركات مسجلة لهذه المادة.")
        else:
            st.info("لا توجد أصناف لعرضها.")
            
    with tab3:
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("➕ إضافة صنف جديد")
            with st.form("add_item_form", clear_on_submit=True):
                new_name = st.text_input("اسم القطعة:")
                new_cat = st.selectbox("التصنيف:", ["كوشوك", "قطع غيار"])
                new_size = st.text_input("المقاس:")
                new_p_price = st.number_input("سعر الشراء (دينار):", min_value=0.0, step=0.5, format="%.2f")
                add_submit = st.form_submit_button("حفظ الصنف الجديد")
                
                if add_submit:
                    if new_name.strip() == "" or new_size.strip() == "":
                        st.error("يرجى ملء كافة الحقول الأساسية.")
                    else:
                        try:
                            cursor.execute("INSERT INTO items_v3 VALUES (?, ?, ?, 0, ?)", (new_name, new_cat, new_size, new_p_price))
                            conn.commit()
                            st.success(f"تم قبول المادة بنجاح! تمت إضافة الصنف '{new_name}'.")
                            st.rerun()
                        except sqlite3.IntegrityError:
                            st.error("خطأ: هذا الصنف بنفس المقاس موجود مسبقاً.")
                            
        with col2:
            st.subheader("❌ حذف صنف من المستودع")
            cursor.execute("SELECT item_name, size FROM items_v3")
            delete_list = {f"{r[0]} | المقاس: {r[1]}": (r[0], r[1]) for r in cursor.fetchall()}
            if delete_list:
                selected_delete = st.selectbox("اختر الصنف المراد حذفه:", list(delete_list.keys()))
                delete_btn = st.button("تأكيد الحذف")
                if delete_btn:
                    item_to_del, size_to_del = delete_list[selected_delete]
                    cursor.execute("DELETE FROM transactions_v3 WHERE item_name = ? AND size = ?", (item_to_del, size_to_del))
                    cursor.execute("DELETE FROM items_v3 WHERE item_name = ? AND size = ?", (item_to_del, size_to_del))
                    conn.commit()
                    st.success("تم حذف المادة بالكامل بنجاح.")
                    st.rerun()
            else:
                st.info("لا توجد أصناف لحذفها.")
                
    with tab4:
        st.subheader("🟢 جرد ومطابقة المخزون")
        col_a, col_b = st.columns(2)
        with col_a:
            audit_date = st.date_input("جرد لغاية تاريخ معين:", value=datetime.now())
        with col_b:
            cursor.execute("SELECT item_name, size, current_stock FROM items_v3")
            audit_items = cursor.fetchall()
            audit_list = {f"{r[0]} | {r[1]}": (r[0], r[1], r[2]) for r in audit_items}
            
            if audit_list:
                selected_audit = st.selectbox("اختر الصنف لمطابقته:", list(audit_list.keys()))
                physical_qty = st.number_input("الكمية الفعلية الموجودة على الرف:", min_value=0, step=1)
                audit_submit = st.button("تأكيد المطابقة والجرد")
                
                if audit_submit:
                    item_name, size, system_qty = audit_list[selected_audit]
                    status = "مطابق 🟢" if system_qty == physical_qty else "غير مطابق 🔴"
                    
                    cursor.execute(
                        "INSERT INTO audits_v3 (item_name, size, audit_date, system_qty, physical_qty, status) VALUES (?, ?, ?, ?, ?, ?)",
                        (item_name, size, audit_date.strftime('%Y-%m-%d'), system_qty, physical_qty, status)
                    )
                    conn.commit()
                    if status == "مطابق 🟢":
                        st.success(f"النتيجة: مطابق 🟢 تم إعطاء الضوء الأخضر!")
                    else:
                        st.error(f"النتيجة: غير مطابق 🔴 يوجد فرق مخزني.")
                    st.rerun()

        st.divider()
        st.subheader("📋 كشف الجرد السابق")
        cursor.execute("SELECT item_name, size, audit_date, system_qty, physical_qty, status FROM audits_v3 ORDER BY audit_id DESC")
        audits_data = cursor.fetchall()
        if audits_data:
            df_audits = pd.DataFrame(audits_data, columns=["اسم الصنف", "المقاس", "تاريخ الجرد", "الكمية بالنظام", "الكمية الفعلية", "حالة الجرد"])
            df_audits.index = range(1, len(df_audits) + 1)
            df_audits.index.name = "ت"
            st.dataframe(df_audits, use_container_width=True)
        else:
            st.info("لم يتم تسجيل أي عملية جرد بعد.")

    with tab5:
        st.subheader("👥 إدارة حسابات الموظفين وكلمات السر")
        col_u1, col_u2 = st.columns(2)
        with col_u1:
            st.subheader("➕ إضافة مستخدم جديد")
            with st.form("add_user_form", clear_on_submit=True):
                new_username = st.text_input("اسم الموظف (باللغة العربية):")
                new_pass = st.text_input("كلمة السر الجديدة:")
                new_role = st.selectbox("الصلاحية:", ["Worker", "Admin"])
                user_submit = st.form_submit_button("حفظ المستخدم")
                if user_submit:
                    if new_username.strip() == "" or new_pass.strip() == "":
                        st.error("يرجى ملء جميع الحقول.")
                    else:
                        try:
                            cursor.execute("INSERT INTO users_v3 VALUES (?, ?, ?)", (new_username, new_pass, new_role))
                            conn.commit()
                            st.success(f"تمت إضافة المستخدم {new_username} بنجاح.")
                            st.rerun()
                        except sqlite3.IntegrityError:
                            st.error("اسم المستخدم مسجّل مسبقاً.")
        
        with col_u2:
            st.subheader("❌ حذف مستخدم")
            cursor.execute("SELECT username FROM users_v3 WHERE username != 'المدير'")
            user_list = [r[0] for r in cursor.fetchall()]
            if user_list:
                selected_user_del = st.selectbox("اختر المستخدم المراد حذفه:", user_list)
                user_del_btn = st.button("تأكيد حذف المستخدم")
                if user_del_btn:
                    cursor.execute("DELETE FROM users_v3 WHERE username = ?", (selected_user_del,))
                    conn.commit()
                    st.success(f"تم حذف حساب {selected_user_del} بنجاح.")
                    st.rerun()
            else:
                st.info("لا توجد حسابات أخرى لحذفها.")
else:
    st.info("الرجاء تسجيل الدخول من القائمة الجانبية لبدء العمل.")

conn.close()
