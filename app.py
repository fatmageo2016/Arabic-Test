import streamlit as st
import pandas as pd
import time
import random
import re
import unicodedata

# دالة لتطبيع النص العربي (توحيد الهمزات، حذف التشكيل، إزالة المسافات الزائدة)
def normalize_arabic(text):
    text = str(text).strip()
    # توحيد أشكال الهمزة: أ إ آ ➜ ا
    text = re.sub(r'[أإآ]', 'ا', text)
    # حذف حرف التاء المربوطة وتحويلها لهاء
    text = re.sub(r'ة', 'ه', text)
    # حذف الشدة والحركات (التشكيل)
    text = re.sub(r'[\u064B-\u065F\u0670]', '', text)
    # إزالة المسافات الزائدة
    text = re.sub(r'\s+', ' ', text).strip()
    return text

# 1. إعدادات الصفحة الأساسية
st.set_page_config(page_title="منصة التقييم التكيفي - د. فداء", layout="centered")

# 2. تصميم الواجهة (RTL) وتحسين المظهر
st.markdown("""
    <style>
    .main, .stApp { direction: RTL; text-align: right; }
    .header-box { background-color: #1e3d59; color: white; padding: 20px; border-radius: 15px; text-align: center; margin-bottom: 20px; }
    .question-card { background-color: white; padding: 25px; border-radius: 20px; box-shadow: 0 4px 10px rgba(0,0,0,0.05); border-right: 10px solid #ff6e40; margin-top: 20px; }
    .stButton>button { width: 100%; border-radius: 12px; height: 3.5em; background-color: #1e3d59; color: white; font-weight: bold; }
    .timer-text { font-size: 20px; color: #dc3545; font-weight: bold; direction: LTR; }
    .error-box { background-color: #fff3f3; padding: 15px; border-radius: 10px; border-right: 5px solid #dc3545; margin-bottom: 10px; text-align: right; }
    div[data-testid="stRadio"] > label { text-align: right; direction: RTL; }
    </style>
    """, unsafe_allow_html=True)

# 3. دالة تحميل البيانات (تم التعديل لتدعم التنسيق الجديد)
@st.cache_data # تحسين الأداء عبر تخزين البيانات مؤقتاً
def load_data():
    try:
        # قراءة الملف (تأكدي أن اسم الملف هو questions.xlsx)
        df = pd.read_excel("questions.xlsx", engine='openpyxl')
        # تنظيف أسماء الأعمدة من أي مسافات زائدة
        df.columns = [str(c).strip() for c in df.columns]
        return df
    except Exception as e:
        st.error(f"⚠️ خطأ: لا يمكن قراءة ملف questions.xlsx. تأكدي من رفعه وتسمية الأعمدة كما اتفقنا. {e}")
        return None

df = load_data()

# 4. إعداد حالة الجلسة (Session State)
if 'step' not in st.session_state:
    st.session_state.update({
        'step': 'login', 'name': '', 'email': '', 'score': 0, 'count': 0,
        'level': 2, 'asked_ids': [], 'current_q': None, 'answered': False,
        'start_time': None, 'end_time': None, 'errors_log': [], 'shuffled_opts': []
    })

# --- القائمة الجانبية للمعلمة ---
with st.sidebar:
    st.header("🔐 بوابة المعلمة")
    pwd = st.text_input("كلمة المرور:", type="password")
    if pwd == "1234":
        st.success("مرحباً د. فداء")
        if st.session_state.name:
            st.write(f"**الطالب:** {st.session_state.name}")
            st.write(f"**المستوى الحالي:** {st.session_state.level}")
            st.write(f"**الأخطاء:** {len(st.session_state.errors_log)}")
        else: st.info("لا يوجد طالب نشط")
    elif pwd: st.error("خطأ!")

# --- الهيدر الرئيسي ---
st.markdown("<div class='header-box'><h1>منصة التقييم اللغوي التكيفي</h1><p>إشراف الدكتورة: <b>فداء الإسلام</b></p></div>", unsafe_allow_html=True)

# --- المرحلة 1: التسجيل ---
if st.session_state.step == 'login':
    st.markdown("<div class='question-card'>", unsafe_allow_html=True)
    st.subheader("📝 تسجيل بيانات الطالب")
    name = st.text_input("الاسم الثلاثي:")
    email = st.text_input("البريد الإلكتروني:")
    st.info("سيتم عرض 10 أسئلة تتكيف مع مستواك الإجمالي")
    if st.button("بدء الاختبار 🚀"):
        if name and email:
            st.session_state.update({'name': name, 'email': email, 'step': 'quiz', 'start_time': time.time()})
            st.rerun()
        else: st.warning("يرجى إكمال البيانات")
    st.markdown("</div>", unsafe_allow_html=True)

# --- المرحلة 2: الاختبار ---
elif st.session_state.step == 'quiz' and st.session_state.count < 10:
    if df is not None:
        elapsed = int(time.time() - st.session_state.start_time)
        mins, secs = divmod(elapsed, 60)
        
        c1, c2 = st.columns([4, 1])
        with c1: st.write(f"السؤال {st.session_state.count + 1} من 10")
        with c2: st.markdown(f"<span class='timer-text'>{mins:02d}:{secs:02d}</span>", unsafe_allow_html=True)
        st.progress(st.session_state.count / 10)

        # اختيار سؤال جديد (تم تعديل أسماء الأعمدة لتطابق الإنجليزية)
        if st.session_state.current_q is None:
            pool = df[(df['Difficulty'] == st.session_state.level) & (~df['ID'].isin(st.session_state.asked_ids))]
            if pool.empty: 
                pool = df[~df['ID'].isin(st.session_state.asked_ids)]
            
            if not pool.empty:
                st.session_state.current_q = pool.sample(1).iloc[0]
                st.session_state.answered = False
                # خلط الخيارات عشوائياً وتخزينها
                opts_list = [str(st.session_state.current_q['Option_A']),
                             str(st.session_state.current_q['Option_B']),
                             str(st.session_state.current_q['Option_C'])]
                random.shuffle(opts_list)
                st.session_state.shuffled_opts = opts_list
            else:
                st.session_state.step = 'result'; st.rerun()

        q = st.session_state.current_q

        # عرض السؤال (العمود اسمه Question)
        st.markdown(f"<div class='question-card'><h4>{q['Question']}</h4></div>", unsafe_allow_html=True)
        
        # الخيارات المخلوطة عشوائياً
        opts = st.session_state.shuffled_opts
        ans = st.radio("اختر الإجابة الصحيحة:", opts, index=None, key=f"q_{st.session_state.count}", disabled=st.session_state.answered)

        if not st.session_state.answered:
            if st.button("تأكيد الإجابة ✅"):
                if ans:
                    st.session_state.answered = True
                    st.session_state.asked_ids.append(q['ID'])
                    correct = str(q['Correct']).strip() # العمود اسمه Correct
                    
                    if normalize_arabic(ans) == normalize_arabic(correct):
                        st.success("إجابة صحيحة! أحسنتِ.")
                        st.session_state.score += 1
                        st.session_state.level = min(3, st.session_state.level + 1)
                    else:
                        st.error(f"للأسف خطأ. الإجابة الصحيحة هي: {correct}")
                        st.session_state.level = max(1, st.session_state.level - 1)
                        st.session_state.errors_log.append({
                            'q': q['Question'], 'y': ans, 'c': correct, 'f': q['Feedback'] # العمود اسمه Feedback
                        })
                    
                    st.info(f"💡 توضيح: {q['Feedback']}")
                    st.button("السؤال التالي ➡️")
                else: st.warning("الرجاء اختيار إجابة")
        else:
            if st.button("السؤال التالي ➡️"):
                st.session_state.count += 1
                st.session_state.current_q = None
                if st.session_state.count >= 10:
                    st.session_state.end_time = time.time()
                    st.session_state.step = 'result'
                st.rerun()

# --- المرحلة 3: النتيجة النهائية ---
elif st.session_state.step == 'result':
    st.balloons()
    final_score = st.session_state.score
    total_time = int(st.session_state.end_time - st.session_state.start_time)
    tm, ts = divmod(total_time, 60)
    
    lvl = "متقدم" if final_score >= 8 else "متوسط" if final_score >= 5 else "مبتدئ"
    clr = "#28a745" if final_score >= 8 else "#ffc107" if final_score >= 5 else "#dc3545"

    st.markdown(f"""
        <div class='question-card' style='text-align:center; border-right:none; border-top:10px solid {clr};'>
            <h2 style='color: {clr};'>🏆 اكتمل الاختبار بنجاح</h2>
            <p>اسم الطالب: <b>{st.session_state.name}</b></p>
            <hr>
            <h3>الدرجة النهائية: {final_score} من 10</h3>
            <p>الوقت المستغرق: {tm} دقيقة و {ts} ثانية</p>
            <div style='background:{clr}; color:white; padding:10px 30px; border-radius:50px; display:inline-block;'>
                المستوى التقديري: {lvl}
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    if st.session_state.errors_log:
        st.subheader("🔍 مراجعة الأخطاء والتقييم:")
        for err in st.session_state.errors_log:
            st.markdown(f"""
                <div class='error-box'>
                    <b>السؤال:</b> {err['q']}<br>
                    ❌ <b>إجابتك:</b> {err['y']}<br>
                    ✅ <b>الصحيح:</b> {err['c']}<br>
                    💡 <b>القاعدة:</b> {err['f']}
                </div>
            """, unsafe_allow_html=True)
    
    if st.button("إعادة الاختبار لطالب آخر 🔄"):
        for key in list(st.session_state.keys()): del st.session_state[key]
        st.rerun()
