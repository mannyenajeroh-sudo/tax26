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
    /* Mobile-First Button Styling */
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        height: 3.5em;
        background-color: #008751; 
        color: white;
        font-weight: 800; 
        font-size: 18px;
        border: none;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        transition: all 0.3s;
    }
    .stButton>button:hover {
        background-color: #006b3f;
        transform: translateY(-2px);
    }
    
    /* Typography */
    .big-font {
        font-size: 32px !important;
        font-weight: 900;
        color: #111;
    }
    .tax-header {
        font-size: 18px;
        color: #555;
        font-weight: bold;
        text-transform: uppercase;
        margin-bottom: -5px;
    }
    
    /* Advice Box Styling */
    .advice-box {
        background-color: #f1f8e9;
        border-left: 5px solid #008751;
        padding: 15px;
        border-radius: 5px;
        margin-top: 15px;
        font-size: 15px;
        color: #2e7d32;
    }
    .warning-box {
        background-color: #ffebee;
        border-left: 5px solid #d32f2f;
        padding: 15px;
        border-radius: 5px;
        margin-top: 15px;
        font-size: 15px;
        color: #c62828;
    }
    </style>
""", unsafe_allow_html=True)

# --- 3. ASSET LOADER (Cached) ---
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

# --- 4. LOGIC CONSTANTS (UPDATED NTA 2025) ---
MIN_WAGE_THRESHOLD = 840000 
RENT_RELIEF_CAP = 500000 # Capped at 500k
RENT_RELIEF_RATE = 0.20 # 20% of Rent Paid
PENSION_RATE = 0.08 # 8% Statutory
# UPDATED SME THRESHOLD per signed Act
SMALL_CO_TURNOVER = 100000000 # 100 Million
SMALL_CO_ASSETS = 250000000
CIT_RATE = 0.30
DEV_LEVY_RATE = 0.04

# --- 5. CALCULATION ENGINES (Cached for Speed) ---

@st.cache_data
def calculate_nta_2025_individual(gross_income, rent_paid, pension_vol=0, life_insurance=0, nhf=0):
    # 1. Statutory Deduction (Standard 8% Pension)
    statutory_pension = gross_income * PENSION_RATE
    
    # 2. Total Tax Exempt Deductions (Statutory + Voluntary)
    total_exempt = statutory_pension + pension_vol + life_insurance + nhf
    
    # 3. Rent Relief (Capped at 500k)
    rent_relief = min(RENT_RELIEF_CAP, rent_paid * RENT_RELIEF_RATE)
    
    # 4. Total Reliefs
    # Note: CRA is REMOVED. The new 0% band replaces it.
    total_deductions = total_exempt + rent_relief
    
    # 5. Chargeable Income
    chargeable = max(0, gross_income - total_deductions)
    
    if chargeable <= 0:
        return 0.0, total_deductions
    
    # 6. Progressive Tax Bands (NTA 2025)
    tax = 0
    remaining = chargeable
    
    # Band 1: First 800k @ 0%
    taxable_0 = min(remaining, 800000)
    tax += taxable_0 * 0.00
    remaining -= taxable_0
    
    # Band 2: Next 2.2m @ 15%
    if remaining > 0:
        taxable_15 = min(remaining, 2200000)
        tax += taxable_15 * 0.15
        remaining -= taxable_15
        
    # Band 3: Next 9m @ 18%
    if remaining > 0:
        taxable_18 = min(remaining, 9000000)
        tax += taxable_18 * 0.18
        remaining -= taxable_18
        
    # Band 4: Next 13m @ 21%
    if remaining > 0:
        taxable_21 = min(remaining, 13000000)
        tax += taxable_21 * 0.21
        remaining -= taxable_21
        
    # Band 5: Next 25m @ 23%
    if remaining > 0:
        taxable_23 = min(remaining, 25000000)
        tax += taxable_23 * 0.23
        remaining -= taxable_23
        
    # Band 6: Balance @ 25%
    if remaining > 0:
        tax += remaining * 0.25
        
    return tax, total_deductions

@st.cache_data
def calculate_pita_2011_individual(gross_income):
    # Old Logic (For Comparison Only)
    pension = gross_income * PENSION_RATE
    # Old CRA: 200k + 20%
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

@st.cache_data
def calculate_freelancer_tax(gross_income, expenses_total, rent_paid):
    assessable_profit = max(0, gross_income - expenses_total)
    
    if assessable_profit <= MIN_WAGE_THRESHOLD: return 0.0, assessable_profit
    
    rent_relief = min(RENT_RELIEF_CAP, rent_paid * RENT_RELIEF_RATE)
    chargeable = max(0, assessable_profit - rent_relief)
    
    # Using NTA 2025 Bands for consistency
    tax = 0
    remaining = chargeable
    
    # Band 1: First 800k @ 0%
    taxable_0 = min(remaining, 800000)
    remaining -= taxable_0
    
    # Band 2: Next 2.2m @ 15%
    if remaining > 0:
        taxable_15 = min(remaining, 2200000)
        tax += taxable_15 * 0.15
        remaining -= taxable_15
        
    # ... Simplified for freelance estimation (using top bands)
    if remaining > 0:
        tax += remaining * 0.25 # Conservative estimate for higher brackets
        
    return tax, assessable_profit

@st.cache_data
def calculate_corporate_tax(turnover, assets, profit, is_prof_service):
    # Updated threshold: 100 Million
    is_small = (turnover <= SMALL_CO_TURNOVER) and (assets <= SMALL_CO_ASSETS) and (not is_prof_service)
    if is_small: return 0.0, 0.0, "Small Company (Exempt from CIT)"
    else: return profit * CIT_RATE, profit * DEV_LEVY_RATE, "Large/Medium Company"

@st.cache_data
def calculate_diaspora_tax(days, foreign_inc, rent_inc, div_inc):
    if days < 183:
        tax = (rent_inc * 0.10) + (div_inc * 0.10)
        return tax, "Non-Resident (Exempt from Global Tax)", True
    else:
        global_inc = foreign_inc + rent_inc + div_inc
        tax, _ = calculate_nta_2025_individual(global_inc, 0)
        return tax, "Tax Resident (Global Income Taxable)", False

@st.cache_data
def calculate_wht(amount, transaction_type, has_tin):
    # Updated Rates 2024/2025
    rates = {
        "Consultancy/Professional": 0.05, 
        "Construction": 0.02, 
        "Supply": 0.02, 
        "Director Fees": 0.15,
        "Dividends": 0.10
    }
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

# --- 6. IMAGE GENERATORS (Optimized) ---
def generate_paye_card(old_tax, new_tax, pct_change, gross_income, is_incognito=False):
    width, height = 1200, 800
    is_increase = new_tax > old_tax
    
    if is_increase:
        bg_color, text_color, emoji, title_text = "#8B0000", "#FFD700", "😭", "BREAKFAST SERVED"
    else:
        bg_color, text_color, emoji, title_text = "#004d33", "#FFFFFF", "🚀", "JUBILATION TIME"

    img = Image.new('RGB', (width, height), color=bg_color)
    d = ImageDraw.Draw(img)
    
    try: 
        font_header = ImageFont.truetype("arialbd.ttf", 70)
        font_title = ImageFont.truetype("arialbd.ttf", 100)
        font_number = ImageFont.truetype("arialbd.ttf", 130)
        font_label = ImageFont.truetype("arialbd.ttf", 50)
        font_small = ImageFont.truetype("arial.ttf", 35)
    except: 
        font_header = ImageFont.load_default()
        font_title = ImageFont.load_default()
        font_number = ImageFont.load_default()
        font_label = ImageFont.load_default()
        font_small = ImageFont.load_default()

    d.text((width/2, 80), "taX26 REPORT 🇳🇬", font=font_header, fill="#DDD", anchor="mm")
    d.text((width/2, 180), f"{title_text} {emoji}", font=font_title, fill=text_color, anchor="mm")
    
    if not is_incognito:
        d.text((width/2, 270), get_percentile_text(gross_income), font=font_label, fill="#ADD8E6", anchor="mm")

    d.rectangle([50, 320, 1150, 680], outline="white", width=8)

    if is_incognito:
        d.text((width/2, 380), "TAX IMPACT", font=font_header, fill="white", anchor="mm")
        sign = "+" if is_increase else ""
        d.text((width/2, 500), f"{sign}{pct_change:.1f}%", font=font_number, fill=text_color, anchor="mm")
        d.text((width/2, 620), "(Incognito Mode 🕵️)", font=font_small, fill="#EEE", anchor="mm")
    else:
        d.text((300, 380), "OLD TAX (2011)", font=font_label, fill="#EEE", anchor="mm")
        d.text((300, 480), f"₦{old_tax:,.0f}", font=font_number, fill="white", anchor="mm")
        d.line([(600, 320), (600, 680)], fill="white", width=5)
        d.text((900, 380), "NEW TAX (2025)", font=font_label, fill="#EEE", anchor="mm")
        d.text((900, 480), f"₦{new_tax:,.0f}", font=font_number, fill=text_color, anchor="mm")
        sign = "+" if is_increase else ""
        d.text((width/2, 620), f"Change: {sign}{pct_change:.1f}%", font=font_label, fill="#ADD8E6", anchor="mm")

    d.text((width/2, 750), "Powered by taX26 | www.tax26.ng", font=font_small, fill="#AAA", anchor="mm")
    
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

def generate_wht_cert(client_name, amount, wht_deducted, net_payout):
    width, height = 1000, 1200
    img = Image.new('RGB', (width, height), color="#FFFFFF")
    d = ImageDraw.Draw(img)
    
    try: 
        font_header = ImageFont.truetype("arialbd.ttf", 70)
        font_title = ImageFont.truetype("arialbd.ttf", 90)
        font_label = ImageFont.truetype("arialbd.ttf", 45)
        font_val_huge = ImageFont.truetype("arialbd.ttf", 140)
        font_val_med = ImageFont.truetype("arialbd.ttf", 80)
        font_sm = ImageFont.truetype("arial.ttf", 35)
    except: 
        font_header = ImageFont.load_default()
        font_title = ImageFont.load_default()
        font_label = ImageFont.load_default()
        font_val_huge = ImageFont.load_default()
        font_val_med = ImageFont.load_default()
        font_sm = ImageFont.load_default()

    d.rectangle([0, 0, width, 200], fill="#003366")
    d.text((width/2, 70), "taX26 🇳🇬", font=font_header, fill="#DDD", anchor="mm")
    d.text((width/2, 150), "WHT CREDIT NOTE", font=font_title, fill="white", anchor="mm")

    y = 280
    d.text((width/2, y), "CLIENT:", font=font_label, fill="#555", anchor="mm")
    d.text((width/2, y+70), client_name, font=font_val_med, fill="#000", anchor="mm")
    
    y += 200
    d.text((width/2, y), "GROSS AMOUNT:", font=font_label, fill="#555", anchor="mm")
    d.text((width/2, y+80), f"₦{amount:,.2f}", font=font_val_med, fill="#333", anchor="mm")
    
    y += 200
    d.text((width/2, y), "WHT DEDUCTED (CREDIT):", font=font_label, fill="#B22222", anchor="mm")
    d.text((width/2, y+100), f"- ₦{wht_deducted:,.2f}", font=font_val_huge, fill="#B22222", anchor="mm")
    
    y += 200
    d.text((width/2, y), "NET PAYOUT:", font=font_title, fill="#003366", anchor="mm")
    d.text((width/2, y+120), f"₦{net_payout:,.2f}", font=font_val_huge, fill="#008000", anchor="mm")
    
    d.text((width/2, height-80), "Generated by taX26 App | Valid for Tax Records", font=font_sm, fill="#777", anchor="mm")

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

# --- 7. MAIN APP UI ---
def main():
    st.title("taX26 Compliance Suite 🇳🇬")
    
    # NAVIGATION TABS
    tab1, tab2, tab3 = st.tabs(["👤 Personal & Salary", "🏢 Business & Directors", "🛠️ Tools & Guides"])
    
    # --- TAB 1: PERSONAL ---
    with tab1:
        st.write("#### Personal Income Tax (PAYE)")
        profile = st.radio("Select Profile", ["Salary Earner", "Freelancer"], horizontal=True)
        
        if profile == "Salary Earner":
            col1, col2 = st.columns(2)
            gross = col1.number_input("Annual Gross Income (₦)", 0.0, step=100000.0, format="%.2f")
            rent = col2.number_input("Annual Rent Paid (₦)", 0.0, step=50000.0, format="%.2f")
            
            # --- FEATURE 1: TAX SAVER SIMULATOR ---
            with st.expander("💰 Tax Saver: Voluntary Contributions"):
                st.markdown("""
                <div class="advice-box">
                <b>Street Smart Tip:</b> Pension and Life Insurance are <b>Tax Free</b>. 
                Instead of paying that money to FIRS, put it in your own future!
                </div>
                """, unsafe_allow_html=True)
                pension_vol = st.number_input("Add Voluntary Pension (Annual)", 0.0, step=50000.0)
                life_ins = st.number_input("Add Life Insurance Premium", 0.0, step=50000.0)
                nhf = st.number_input("Add NHF Contribution", 0.0, step=20000.0)

            if st.button("Calculate My Tax Liability"):
                tax_new, deductions = calculate_nta_2025_individual(gross, rent, pension_vol, life_ins, nhf)
                tax_old = calculate_pita_2011_individual(gross)
                diff = tax_new - tax_old
                
                pct_change = ((tax_new - tax_old) / tax_old * 100) if tax_old > 0 else (100 if tax_new > 0 else 0)

                st.divider()
                
                # HTML PREVIEW (Fast)
                c1, c2 = st.columns(2)
                c1.markdown(f'<div class="tax-header">OLD TAX (2011)</div><div class="big-font">₦{tax_old:,.2f}</div>', unsafe_allow_html=True)
                c2.markdown(f'<div class="tax-header">NEW TAX (2025)</div><div class="big-font">₦{tax_new:,.2f}</div>', unsafe_allow_html=True)
                
                if tax_new == 0:
                    st.success("🎉 You are TAX EXEMPT under the new Minimum Wage threshold!")
                elif diff < 0:
                    st.success(f"🚀 JUBILATION! You save ₦{abs(diff):,.2f} under the new law.")
                    if lottie_celebrate: st_lottie(lottie_celebrate, height=150, key="anim_save")
                else:
                    st.error(f"📉 BREAKFAST SERVED. Your tax increased by ₦{diff:,.2f}.")
                
                # Download Buttons
                st.write("### 📸 Flex Your Status")
                d1, d2 = st.columns(2)
                img_full = generate_paye_card(tax_old, tax_new, pct_change, gross, False)
                d1.download_button("📥 Download Report Card", img_full, "taX26_Report.png", "image/png", use_container_width=True)
                
                img_hide = generate_paye_card(tax_old, tax_new, pct_change, gross, True)
                d2.download_button("🕵️ Download Incognito", img_hide, "taX26_Incognito.png", "image/png", use_container_width=True)

        elif profile == "Freelancer":
            st.info("💡 FIRS taxes **PROFIT**, not Revenue. Deduct your costs first!")
            
            # --- FEATURE 2: EXPENSE SHIELD ---
            with st.expander("🛡️ Freelance Expense Shield"):
                st.markdown('<div class="advice-box">Tick valid business expenses to lower your tax.</div>', unsafe_allow_html=True)
                c1, c2 = st.columns(2)
                e_data = c1.number_input("Internet & Data", 0.0, step=5000.0)
                e_fuel = c2.number_input("Power / Fuel", 0.0, step=10000.0)
                e_soft = c1.number_input("Software / Tools", 0.0, step=20000.0)
                e_dev = c2.number_input("Laptop / Repairs", 0.0, step=50000.0)
                
            gross = st.number_input("Total Revenue (Invoices Paid)", 0.0, step=100000.0)
            rent = st.number_input("Personal Rent", 0.0, step=50000.0)
            
            if st.button("Calculate Freelance Tax"):
                expenses = e_data + e_fuel + e_soft + e_dev
                tax, profit = calculate_freelancer_tax(gross, expenses, rent)
                
                st.divider()
                st.markdown(f"**Gross Revenue:** ₦{gross:,.2f}")
                st.markdown(f"**Valid Expenses:** -₦{expenses:,.2f}")
                st.markdown(f"**Assessable Profit:** ₦{profit:,.2f}")
                st.markdown(f"### Tax Due: ₦{tax:,.2f}")
                
                if expenses > 0:
                    st.success(f"🛡️ Shield Active! You protected ₦{expenses:,.2f} from tax.")

    # --- TAB 2: BUSINESS ---
    with tab2:
        st.write("#### Corporate Tax & Salary Planning")
        
        # --- FEATURE 3: SALARY STRUCTURE ---
        with st.expander("👔 Director Salary Optimizer"):
            st.markdown("""
            <div class="advice-box">
            <b>CEO Tip:</b> Don't pay yourself a flat salary. Structure it to maximize legal allowances 
            (Housing, Transport) which affect how pension is calculated.
            </div>
            """, unsafe_allow_html=True)
            pkg = st.number_input("Total Monthly Package Target (₦)", 0.0, step=50000.0)
            if pkg > 0:
                basic, house, trans = pkg*0.4, pkg*0.3, pkg*0.2
                util = pkg*0.1
                pen = (basic+house+trans) * 0.08
                st.markdown(f"""
                **Optimal Structure:**
                - Basic: ₦{basic:,.2f} | Housing: ₦{house:,.2f} | Transport: ₦{trans:,.2f} | Utility: ₦{util:,.2f}
                - **Pension to Remit:** ₦{pen:,.2f}
                """)
        
        st.divider()
        st.write("**Company Income Tax (CIT) Checker**")
        turn = st.number_input("Annual Turnover", 0.0, step=1000000.0)
        asset = st.number_input("Total Assets", 0.0, step=1000000.0)
        prof = st.number_input("Net Profit", 0.0, step=500000.0)
        is_pro = st.checkbox("Is this a Professional Service? (Audit, Legal, etc)")
        
        if st.button("Check CIT Status"):
            cit, dev, status = calculate_corporate_tax(turn, asset, prof, is_pro)
            tot = cit + dev
            st.markdown(f"**Category:** {status}")
            st.metric("Total Tax Liability", f"₦{tot:,.2f}")
            if tot == 0:
                st.success("✅ Exempt! Turnover is under ₦100M.")

    # --- TAB 3: TOOLS ---
    with tab3:
        tool = st.selectbox("Select Tool", ["WHT Invoice Generator", "Japa Calculator (UK/Canada)", "Inflation Checker"])
        
        if tool == "WHT Invoice Generator":
            st.markdown('<div class="advice-box"><b>WHT is Money!</b> Save this certificate. It is a credit note you can use to pay tax later.</div>', unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            cli = c1.text_input("Client Name")
            amt = c2.number_input("Invoice Amount", 0.0, step=50000.0)
            typ = st.selectbox("Type", ["Consultancy/Professional", "Construction", "Supply", "Director Fees", "Dividends"])
            tin = st.checkbox("I have a TIN", True)
            
            if st.button("Generate WHT Certificate"):
                w, n, r = calculate_wht(amt, typ, tin)
                st.metric("Net Payout", f"₦{n:,.2f}", delta=f"-₦{w:,.2f} WHT ({r*100:.0f}%)")
                cert = generate_wht_cert(cli, amt, w, n)
                st.download_button("📄 Download Certificate", cert, f"WHT_{cli}.png", "image/png", use_container_width=True)
                st.image(cert, caption="Preview", use_container_width=True)

        elif tool == "Japa Calculator (UK/Canada)":
            # --- FEATURE 4: JAPA CALCULATOR ---
            st.subheader("✈️ Purchasing Power Parity (PPP)")
            ng_sal = st.number_input("Current Nigeria Salary (Annual)", 0.0, step=1000000.0)
            dest = st.selectbox("Moving to:", ["London, UK", "Toronto, Canada"])
            
            if st.button("Compare Lifestyle"):
                # Simple Heuristic: 1 GBP in London buys what ~2000 NGN buys in Lagos in terms of LIFESTYLE, not just FX.
                # FX is ~2100. PPP factor reduces value.
                if "UK" in dest:
                    curr, fx, ppp = "£", 2150, 0.4
                else:
                    curr, fx, ppp = "CAD$", 1250, 0.45
                
                equiv = (ng_sal / fx) / ppp
                st.metric(f"Equivalent {curr} Salary Needed", f"{curr}{equiv:,.0f}")
                st.warning(f"To match your **₦{ng_sal:,.0f}** lifestyle in Lagos, you need to earn **{curr}{equiv:,.0f}** abroad. Don't underestimate the cost of rent and tax abroad!")

        elif tool == "Inflation Checker":
            # --- FEATURE 5: INFLATION CHECKER ---
            st.subheader("📉 The 'Sapa' Reality Check")
            sal = st.number_input("Monthly Salary", 0.0, step=50000.0)
            if st.button("Check 2021 Value"):
                # ~100% inflation since 2021
                real = sal / 2.3
                st.metric("Real Value (2021 Terms)", f"₦{real:,.2f}", delta="-56% Value")
                st.error(f"Your **₦{sal:,.0f}** today only buys what **₦{real:,.0f}** bought in 2021.")

    # --- FOOTER ---
    st.write("---") 
    phone = "447467395726" 
    msg = urllib.parse.quote("Hi, I need professional help with my tax from taX26.")
    wa_url = f"https://wa.me/{phone}?text={msg}"
    
    st.markdown("### Need Professional Help?")
    st.markdown(f"""
    <div style="display: flex; justify-content: left; margin-bottom: 20px;">
        <a href="{wa_url}" target="_blank" style="text-decoration: none;">
            <button style="background-color:#25D366; color:white; border:none; padding:10px 20px; border-radius:5px; font-size:16px; font-weight:bold; cursor:pointer; display:flex; align-items:center; gap:10px;">
                💬 Chat with Webcompliance Ltd on WhatsApp
            </button>
        </a>
    </div>
    """, unsafe_allow_html=True)
    st.caption("Disclaimer: This tool is for educational purposes only. Powered by Webcompliance Limited.")

if __name__ == "__main__":
    main()
