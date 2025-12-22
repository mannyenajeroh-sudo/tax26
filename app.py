import streamlit as st
import requests
from streamlit_lottie import st_lottie
from PIL import Image, ImageDraw, ImageFont
import io
import urllib.parse 

# --- 1. APP CONFIGURATION ---
st.set_page_config(
    page_title="taX26 🇳🇬",
    page_icon="🇳🇬",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- 2. CUSTOM CSS ---
st.markdown("""
    <style>
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        height: 3.5em;
        background-color: #008751; 
        color: white;
        font-weight: 800; /* Extra Bold */
        font-size: 18px;
    }
    .stButton>button:hover {
        background-color: #006b3f;
        color: white;
    }
    .big-font {
        font-size: 32px !important;
        font-weight: 900;
        color: #111;
    }
    .tax-header {
        font-size: 20px;
        color: #444;
        font-weight: bold;
        margin-bottom: -8px;
    }
    </style>
""", unsafe_allow_html=True)

# --- 3. ASSET LOADER ---
@st.cache_data
def load_lottieurl(url: str):
    try:
        r = requests.get(url, timeout=3)
        if r.status_code != 200: return None
        return r.json()
    except: return None

# Animation URLs
lottie_money = load_lottieurl("https://lottie.host/5a70422c-7a6c-4860-9154-00100780164c/3d6H2k7i4z.json") 
lottie_celebrate = load_lottieurl("https://lottie.host/4b85994e-2895-4b07-8840-79873998782d/P7j15j2K4z.json") 

# --- 4. LOGIC CONSTANTS ---
MIN_WAGE_THRESHOLD = 840000 
RENT_RELIEF_CAP = 500000
RENT_RELIEF_RATE = 0.20
PENSION_RATE = 0.08
SMALL_CO_TURNOVER = 50000000
SMALL_CO_ASSETS = 250000000
CIT_RATE = 0.30
DEV_LEVY_RATE = 0.04

# --- 5. CALCULATION ENGINES ---
def calculate_nta_2025_individual(gross_income, rent_paid):
    if gross_income <= MIN_WAGE_THRESHOLD: return 0.0
    pension = gross_income * PENSION_RATE
    rent_relief = min(RENT_RELIEF_CAP, rent_paid * RENT_RELIEF_RATE)
    chargeable = max(0, gross_income - pension - rent_relief)
    
    tax = 0
    remaining = chargeable
    bands = [(800000, 0.00), (2200000, 0.15), (9000000, 0.18), (13000000, 0.21), (25000000, 0.23), (float('inf'), 0.25)]
    for limit, rate in bands:
        if remaining <= 0: break
        taxable = min(remaining, limit)
        tax += taxable * rate
        remaining -= taxable
    return tax

def calculate_pita_2011_individual(gross_income):
    pension = gross_income * PENSION_RATE
    cra = max(200000, 0.01 * gross_income) + (0.20 * gross_income)
    chargeable = max(0, gross_income - pension - cra)
    
    tax = 0
    remaining = chargeable
    bands = [(300000, 0.07), (300000, 0.11), (500000, 0.15), (500000, 0.19), (1600000, 0.21), (float('inf'), 0.24)]
    for limit, rate in bands:
        if remaining <= 0: break
        taxable = min(remaining, limit)
        tax += taxable * rate
        remaining -= taxable
    return tax

def calculate_freelancer_tax(gross_income, expenses, rent_paid):
    assessable_profit = max(0, gross_income - expenses)
    if assessable_profit <= MIN_WAGE_THRESHOLD: return 0.0, assessable_profit
    rent_relief = min(RENT_RELIEF_CAP, rent_paid * RENT_RELIEF_RATE)
    chargeable = max(0, assessable_profit - rent_relief)
    tax = 0
    remaining = chargeable
    bands = [(800000, 0.00), (2200000, 0.15), (9000000, 0.18), (13000000, 0.21), (25000000, 0.23), (float('inf'), 0.25)]
    for limit, rate in bands:
        if remaining <= 0: break
        taxable = min(remaining, limit)
        tax += taxable * rate
        remaining -= taxable
    return tax, assessable_profit

def calculate_corporate_tax(turnover, assets, profit, is_prof_service):
    is_small = (turnover <= SMALL_CO_TURNOVER) and (assets <= SMALL_CO_ASSETS) and (not is_prof_service)
    if is_small: return 0.0, 0.0, "Small Company (Exempt)"
    else: return profit * CIT_RATE, profit * DEV_LEVY_RATE, "Large/Medium Company"

def calculate_diaspora_tax(days, foreign_inc, rent_inc, div_inc):
    if days < 183:
        tax = (rent_inc * 0.10) + (div_inc * 0.10)
        return tax, "Non-Resident (Exempt from Global Tax)", True
    else:
        global_inc = foreign_inc + rent_inc + div_inc
        tax = calculate_nta_2025_individual(global_inc, 0)
        return tax, "Tax Resident (Global Income Taxable)", False

def calculate_wht(amount, transaction_type, has_tin):
    rates = {"Consultancy": 0.05, "Supply": 0.02, "Construction": 0.02, "Directors Fees": 0.15}
    base = rates.get(transaction_type, 0.05)
    rate = base * 2 if not has_tin else base
    return amount * rate, amount - (amount*rate), rate

def get_percentile_text(gross_income):
    if gross_income > 100000000: return "TOP 0.1% (BILLIONAIRE 🦅)"
    if gross_income > 50000000: return "TOP 1% (ODOGWU 🦁)"
    if gross_income > 20000000: return "TOP 5% (CHAIRMAN 🧢)"
    if gross_income > 10000000: return "TOP 10% (BIG BOY 💼)"
    if gross_income > 5000000: return "TOP 20% (SENIOR MAN 👊)"
    return "ASPIRING (THE MASSES ✊)"

# --- 6. IMAGE GENERATORS ---

# A. PAYE Report Card (Red/Green)
def generate_paye_card(old_tax, new_tax, pct_change, gross_income, is_incognito=False):
    width, height = 900, 600 # Larger Canvas
    
    is_increase = new_tax > old_tax
    if is_increase:
        bg_color = "#8B0000" # Dark Red
        text_color = "#FFD700" # Gold
        emoji = "😭"
        title_text = "BREAKFAST SERVED"
    else:
        bg_color = "#004d33" # Nigerian Green
        text_color = "#FFFFFF" # White
        emoji = "🚀"
        title_text = "JUBILATION TIME"

    img = Image.new('RGB', (width, height), color=bg_color)
    d = ImageDraw.Draw(img)
    
    # Load fonts (Try-Catch fallback)
    try: 
        font_header = ImageFont.truetype("arialbd.ttf", 60)
        font_title = ImageFont.truetype("arialbd.ttf", 80)
        font_number = ImageFont.truetype("arialbd.ttf", 90) # HUGE numbers
        font_label = ImageFont.truetype("arial.ttf", 40)
        font_small = ImageFont.truetype("arial.ttf", 30)
    except: 
        font_header = ImageFont.load_default()
        font_title = ImageFont.load_default()
        font_number = ImageFont.load_default()
        font_label = ImageFont.load_default()
        font_small = ImageFont.load_default()

    # Draw Text
    d.text((width/2, 60), "taX26 REPORT 🇳🇬", font=font_header, fill="#DDD", anchor="mm")
    d.text((width/2, 140), f"{title_text} {emoji}", font=font_title, fill=text_color, anchor="mm")
    
    if not is_incognito:
        percentile_msg = get_percentile_text(gross_income)
        d.text((width/2, 210), percentile_msg, font=font_label, fill="#ADD8E6", anchor="mm")

    # Data Box
    d.rectangle([50, 240, 850, 500], outline="white", width=5)

    if is_incognito:
        d.text((width/2, 300), "TAX IMPACT", font=font_header, fill="white", anchor="mm")
        sign = "+" if is_increase else ""
        d.text((width/2, 400), f"{sign}{pct_change:.1f}%", font=font_number, fill=text_color, anchor="mm")
        d.text((width/2, 470), "(Incognito Mode 🕵️)", font=font_small, fill="#EEE", anchor="mm")
    else:
        # Columns
        # Old Tax
        d.text((225, 290), "OLD TAX (2011)", font=font_label, fill="#EEE", anchor="mm")
        d.text((225, 360), f"₦{old_tax:,.0f}", font=font_number, fill="white", anchor="mm")
        
        d.line([(450, 250), (450, 490)], fill="white", width=3) # Vertical Line
        
        # New Tax
        d.text((675, 290), "NEW TAX (2025)", font=font_label, fill="#EEE", anchor="mm")
        d.text((675, 360), f"₦{new_tax:,.0f}", font=font_number, fill=text_color, anchor="mm")
        
        sign = "+" if is_increase else ""
        d.text((width/2, 450), f"Change: {sign}{pct_change:.1f}%", font=font_label, fill="#ADD8E6", anchor="mm")

    d.text((width/2, 550), "Powered by taX26 | www.tax26.ng", font=font_small, fill="#AAA", anchor="mm")

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

# B. WHT Certificate Generator (Professional Blue)
def generate_wht_cert(client_name, amount, wht_deducted, net_payout):
    width, height = 900, 600
    bg_color = "#F0F8FF" # Alice Blue (Light professional background)
    
    img = Image.new('RGB', (width, height), color=bg_color)
    d = ImageDraw.Draw(img)
    
    try: 
        font_title = ImageFont.truetype("arialbd.ttf", 60)
        font_val = ImageFont.truetype("arialbd.ttf", 70)
        font_lbl = ImageFont.truetype("arial.ttf", 35)
        font_sm = ImageFont.truetype("arial.ttf", 25)
    except: 
        font_title = ImageFont.load_default()
        font_val = ImageFont.load_default()
        font_lbl = ImageFont.load_default()
        font_sm = ImageFont.load_default()

    # Header Strip
    d.rectangle([0, 0, width, 150], fill="#003366") # Navy Blue Header
    d.text((width/2, 50), "taX26 🇳🇬", font=font_lbl, fill="#DDD", anchor="mm")
    d.text((width/2, 100), "WHT CREDIT NOTE", font=font_title, fill="white", anchor="mm")

    # Content
    d.text((50, 200), "Client:", font=font_lbl, fill="#333", anchor="lm")
    d.text((250, 200), client_name, font=font_lbl, fill="#000", anchor="lm")

    d.text((50, 280), "Gross Amount:", font=font_lbl, fill="#333", anchor="lm")
    d.text((900-50, 280), f"₦{amount:,.2f}", font=font_lbl, fill="#000", anchor="rm")

    d.text((50, 360), "WHT Deducted:", font=font_lbl, fill="#333", anchor="lm")
    d.text((900-50, 360), f"- ₦{wht_deducted:,.2f}", font=font_lbl, fill="#B22222", anchor="rm") # Red text for deduction

    d.line([50, 400, 850, 400], fill="#333", width=2)

    d.text((50, 450), "NET PAYOUT:", font=font_title, fill="#003366", anchor="lm")
    d.text((900-50, 450), f"₦{net_payout:,.2f}", font=font_val, fill="#008000", anchor="rm") # Green text for payout

    d.text((width/2, 560), "Generated by taX26 App | Valid for Record Keeping", font=font_sm, fill="#777", anchor="mm")

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

# --- 7. MAIN APP UI ---
def main():
    st.title("taX26 Compliance Suite 🇳🇬")
    
    # Navigation Tabs
    tab1, tab2, tab3 = st.tabs(["Personal Income", "Business / Corporate", "WHT Certificate Tool"])
    
    # --- TAB 1: PERSONAL ---
    with tab1:
        st.write("#### Calculate Personal Income Tax (PAYE)")
        type_choice = st.radio("Select Profile", ["Salary Earner (PAYE)", "Freelancer / Remote", "Diaspora / Japa"], horizontal=True)
        
        if type_choice == "Salary Earner (PAYE)":
            c1, c2 = st.columns(2)
            gross = c1.number_input("Annual Gross Income (₦)", min_value=0.0, step=100000.0, format="%.2f")
            rent = c2.number_input("Annual Rent Paid (₦)", min_value=0.0, step=50000.0, format="%.2f")
            
            if st.button("Calculate My Tax Liability"):
                tax_new = calculate_nta_2025_individual(gross, rent)
                tax_old = calculate_pita_2011_individual(gross)
                diff = tax_new - tax_old
                if tax_old > 0: pct_change = ((tax_new - tax_old) / tax_old) * 100
                else: pct_change = 100 if tax_new > 0 else 0

                st.divider()

                # Big Display
                col_a, col_b = st.columns(2)
                with col_a:
                    st.markdown('<p class="tax-header">Old Tax (2011)</p>', unsafe_allow_html=True)
                    st.markdown(f'<p class="big-font">₦{tax_old:,.2f}</p>', unsafe_allow_html=True)
                with col_b:
                    st.markdown('<p class="tax-header">New Tax (2025)</p>', unsafe_allow_html=True)
                    st.markdown(f'<p class="big-font">₦{tax_new:,.2f}</p>', unsafe_allow_html=True)

                if diff < 0:
                    if lottie_celebrate: st_lottie(lottie_celebrate, height=150, key="anim_save")
                    st.success(f"Great News! Savings Identified: ₦{abs(diff):,.2f}")
                elif tax_new == 0:
                    st.success("Tax Exempt Status (Minimum Wage)")
                else:
                    st.warning(f"Liability Increased by: ₦{diff:,.2f}")

                # Download Buttons
                st.write("### 📸 Share Report Card")
                d1, d2 = st.columns(2)
                
                img_full = generate_paye_card(tax_old, tax_new, pct_change, gross, False)
                d1.download_button("📥 Download Full Report", data=img_full, file_name="taX26_Report.png", mime="image/png", use_container_width=True)
                
                img_incognito = generate_paye_card(tax_old, tax_new, pct_change, gross, True)
                d2.download_button("🕵️ Download Incognito", data=img_incognito, file_name="taX26_Incognito.png", mime="image/png", use_container_width=True)
                
                st.image(img_full, caption="Preview", use_container_width=True)

        elif type_choice == "Freelancer / Remote":
            st.info("💡 **Tip:** Deduct business expenses before tax.")
            c1, c2 = st.columns(2)
            gross = c1.number_input("Total Earnings", step=100000.0)
            exp = c2.number_input("Business Expenses", step=50000.0)
            rent = st.number_input("Rent (Personal)", step=50000.0)
            
            if st.button("Calculate Freelance Tax"):
                tax, profit = calculate_freelancer_tax(gross, exp, rent)
                st.divider()
                st.markdown(f"**Taxable Profit:** ₦{profit:,.2f}")
                st.markdown(f"**Tax Due:** ₦{tax:,.2f}")

        elif type_choice == "Diaspora / Japa":
            days = st.slider("Days in Nigeria (Last 12 Months)", 0, 365, 30)
            f_inc = st.number_input("Foreign Income (₦)", step=100000.0)
            n_rent = st.number_input("Nig. Rent Income (₦)", step=50000.0)
            n_div = st.number_input("Nig. Dividends (₦)", step=10000.0)
            
            if st.button("Calculate Diaspora Tax"):
                tax, status, is_safe = calculate_diaspora_tax(days, f_inc, n_rent, n_div)
                st.subheader(status)
                st.metric("Total Tax", f"₦{tax:,.2f}")

    # --- TAB 2: BUSINESS ---
    with tab2:
        st.subheader("Corporate Tax Check")
        turn = st.number_input("Annual Turnover", step=1000000.0)
        assets = st.number_input("Total Assets", step=1000000.0)
        profit = st.number_input("Assessable Profit", step=500000.0)
        is_prof = st.checkbox("Professional Services?")
        
        if st.button("Check Corporate Status"):
            cit, dev, status = calculate_corporate_tax(turn, assets, profit, is_prof)
            total = cit + dev
            st.divider()
            st.markdown(f"**Status:** {status}")
            st.metric("Total Liability (CIT + Levy)", f"₦{total:,.2f}")

    # --- TAB 3: WHT TOOLS ---
    with tab3:
        st.subheader("Withholding Tax (WHT) Certificate Generator")
        st.write("Generate a professional credit note to send to your clients.")
        
        col1, col2 = st.columns(2)
        client = col1.text_input("Client Name")
        amt = col2.number_input("Invoice Amount (₦)", step=50000.0)
        t_type = st.selectbox("Transaction Type", ["Consultancy", "Supply", "Construction", "Director Fees"])
        tin = st.checkbox("I have a TIN", value=True)
        
        if st.button("Generate WHT Certificate"):
            wht, net, rate = calculate_wht(amt, t_type, tin)
            
            st.success("Certificate Generated Successfully!")
            st.metric("Net Payout", f"₦{net:,.2f}", delta=f"-₦{wht:,.2f} WHT")
            
            # Generate the specific WHT image
            cert_img = generate_wht_cert(client, amt, wht, net)
            
            # Show download button prominently
            st.download_button(
                label="📄 Download WHT Certificate (Image)",
                data=cert_img,
                file_name=f"WHT_Certificate_{client}.png",
                mime="image/png",
                use_container_width=True
            )
            
            st.image(cert_img, caption="Certificate Preview", use_container_width=True)

    # --- FOOTER ---
    st.write("---") 
    phone = "447467395726" 
    msg = urllib.parse.quote("Hi, I need professional help with my tax from taX26.")
    wa_url = f"https://wa.me/{phone}?text={msg}"
    
    st.markdown("### Need Professional Help?")
    st.markdown(f"""
    <a href="{wa_url}" target="_blank" style="text-decoration: none;">
        <button style="background-color:#25D366; color:white; border:none; padding:10px 20px; border-radius:5px; font-size:16px; font-weight:bold; cursor:pointer; display:flex; align-items:center; gap:10px;">
            💬 Chat with Webcompliance Ltd on WhatsApp
        </button>
    </a>
    """, unsafe_allow_html=True)
    st.caption("Disclaimer: This tool is for educational purposes only. Powered by Webcompliance Limited.")

if __name__ == "__main__":
    main()
