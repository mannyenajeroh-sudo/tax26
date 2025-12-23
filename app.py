import streamlit as st
import requests
from streamlit_lottie import st_lottie
import urllib.parse 

# --- 1. APP CONFIGURATION ---
st.set_page_config(
    page_title="taX26",
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
    
    /* Branding Styling */
    .main-title {
        font-size: 40px !important;
        font-weight: 900 !important;
        color: #000000;
        margin-bottom: -10px !important;
    }
    .sub-title {
        font-size: 18px !important;
        font-weight: 400 !important;
        color: #666;
        margin-top: 0px !important;
        margin-bottom: 30px !important;
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
    
    /* Screenshot Instruction */
    .screenshot-hint {
        text-align: center;
        font-size: 14px;
        color: #666;
        margin-top: 10px;
        font-style: italic;
        background-color: #f8f9fa;
        padding: 8px;
        border-radius: 12px;
        border: 1px dashed #ccc;
        display: block;
        width: 100%;
    }
    </style>
""", unsafe_allow_html=True)

# --- 3. ASSET LOADERS ---
@st.cache_data
def load_lottieurl(url: str):
    try:
        r = requests.get(url, timeout=3)
        if r.status_code != 200: return None
        return r.json()
    except: return None

# Animation URLs
lottie_celebrate = load_lottieurl("https://lottie.host/4b85994e-2895-4b07-8840-79873998782d/P7j15j2K4z.json") 

# --- 4. LOGIC CONSTANTS (NTA 2025) ---
MIN_WAGE_THRESHOLD = 840000 
RENT_RELIEF_CAP = 500000 
RENT_RELIEF_RATE = 0.20 
PENSION_RATE = 0.08 
SMALL_CO_TURNOVER = 100000000 
SMALL_CO_ASSETS = 250000000
CIT_RATE = 0.30
DEV_LEVY_RATE = 0.04

# --- 5. CALCULATION ENGINES ---

@st.cache_data
def calculate_nta_2025_individual(gross_income, rent_paid, pension_vol=0, life_insurance=0, nhf=0):
    statutory_pension = gross_income * PENSION_RATE
    total_exempt = statutory_pension + pension_vol + life_insurance + nhf
    rent_relief = min(RENT_RELIEF_CAP, rent_paid * RENT_RELIEF_RATE)
    total_deductions = total_exempt + rent_relief
    chargeable = max(0, gross_income - total_deductions)
    
    if chargeable <= 0: return 0.0, total_deductions
    
    tax = 0
    remaining = chargeable
    bands = [(800000, 0.00), (2200000, 0.15), (9000000, 0.18), (13000000, 0.21), (25000000, 0.23), (float('inf'), 0.25)]
    
    for limit, rate in bands:
        if remaining <= 0: break
        taxable = min(remaining, limit)
        tax += taxable * rate
        remaining -= taxable
        
    return tax, total_deductions

@st.cache_data
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

@st.cache_data
def calculate_freelancer_tax(gross_income, expenses_total, rent_paid):
    assessable_profit = max(0, gross_income - expenses_total)
    if assessable_profit <= MIN_WAGE_THRESHOLD: return 0.0, assessable_profit
    
    rent_relief = min(RENT_RELIEF_CAP, rent_paid * RENT_RELIEF_RATE)
    chargeable = max(0, assessable_profit - rent_relief)
    
    tax = 0
    remaining = chargeable
    
    # Simplified NTA 2025 Logic
    taxable_0 = min(remaining, 800000)
    remaining -= taxable_0
    
    if remaining > 0:
        tax += remaining * 0.20 
        
    return tax, assessable_profit

@st.cache_data
def calculate_corporate_tax(turnover, assets, profit, is_prof_service):
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
    rates = {"Consultancy/Professional": 0.05, "Construction": 0.02, "Supply": 0.02, "Director Fees": 0.15, "Dividends": 0.10}
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

# --- 6. HTML CARD RENDERERS (CLEANED) ---

def render_paye_card_html(old_tax, new_tax, pct_change, gross_income):
    is_increase = new_tax > old_tax
    
    if is_increase:
        bg_color = "linear-gradient(135deg, #8B0000 0%, #b22222 100%)"
        text_color = "#FFD700" # Gold
        emoji = "😭"
        title_text = "BREAKFAST SERVED"
        verdict = f"Damage: +{pct_change:.1f}%"
    else:
        bg_color = "linear-gradient(135deg, #004d33 0%, #008751 100%)"
        text_color = "#FFFFFF" # White
        emoji = "🚀"
        title_text = "JUBILATION TIME"
        verdict = f"Savings: {pct_change:.1f}%"
        
    rank = get_percentile_text(gross_income)

    html = f"""
    <div style="background: {bg_color}; padding: 25px; border-radius: 15px; color: white; font-family: sans-serif; border: 3px solid white; box-shadow: 0 10px 25px rgba(0,0,0,0.3); margin-bottom: 10px;">
        <div style="text-align: center; font-weight: 900; font-size: 24px; letter-spacing: 1px; color: white; text-shadow: 1px 1px 3px rgba(0,0,0,0.5);">taX26 REPORT CARD 🇳🇬</div>
        <div style="text-align: center; font-size: 32px; font-weight: 900; margin: 10px 0; color: {text_color}; text-shadow: 2px 2px 4px rgba(0,0,0,0.3); line-height: 1.2;">
            {title_text} {emoji}
        </div>
        <div style="text-align: center; font-size: 12px; margin-bottom: 25px; color: #ADD8E6; font-weight: normal; opacity: 0.9;">
            {rank}
        </div>
        <div style="background: rgba(255,255,255,0.15); border-radius: 12px; padding: 20px; display: flex; justify-content: space-between; align-items: center;">
            <div style="text-align: center; flex: 1;">
                <div style="font-size: 12px; opacity: 0.8;">OLD TAX (2011)</div>
                <div style="font-size: 20px; font-weight: bold;">₦{old_tax:,.0f}</div>
            </div>
            <div style="width: 2px; height: 40px; background: rgba(255,255,255,0.3); margin: 0 10px;"></div>
            <div style="text-align: center; flex: 1;">
                <div style="font-size: 12px; opacity: 0.8;">NEW TAX (2025)</div>
                <div style="font-size: 20px; font-weight: 900; color: {text_color};">₦{new_tax:,.0f}</div>
            </div>
        </div>
        <div style="text-align: center; margin-top: 15px; font-weight: bold; font-size: 18px;">
            {verdict}
        </div>
        <div style="text-align: center; margin-top: 20px; font-size: 10px; opacity: 0.6;">
            POWERED BY taX26 | SCREENSHOT TO SAVE 📸
        </div>
    </div>
    """
    return html

def render_wht_card_html(vendor_name, client_name, amount, wht_deducted, net_payout):
    html = f"""
    <div style="background-color: white; border: 2px solid #003366; border-radius: 12px; overflow: hidden; font-family: sans-serif; box-shadow: 0 5px 15px rgba(0,0,0,0.1); margin-bottom: 10px;">
        <div style="background-color: #003366; color: white; padding: 20px; text-align: center;">
            <div style="font-size: 12px; opacity: 0.8;">taX26 OFFICIAL 🇳🇬</div>
            <div style="font-size: 22px; font-weight: 900; letter-spacing: 1px;">WHT CREDIT NOTE</div>
        </div>
        <div style="padding: 25px; color: #333;">
            <div style="margin-bottom: 15px;">
                <div style="font-size: 11px; color: #666; text-transform: uppercase; font-weight: bold;">Vendor (Beneficiary)</div>
                <div style="font-size: 18px; font-weight: bold; color: black;">{vendor_name}</div>
            </div>
            <div style="margin-bottom: 20px;">
                <div style="font-size: 11px; color: #666; text-transform: uppercase; font-weight: bold;">Client (Payer)</div>
                <div style="font-size: 18px; font-weight: bold; color: black;">{client_name}</div>
            </div>
            <div style="margin-bottom: 20px; border-bottom: 1px solid #eee; padding-bottom: 15px; border-top: 1px solid #eee; padding-top: 15px;">
                <div style="font-size: 11px; color: #666; text-transform: uppercase; font-weight: bold;">Gross Amount</div>
                <div style="font-size: 18px; font-weight: bold;">₦{amount:,.2f}</div>
            </div>
            <div style="margin-bottom: 20px;">
                <div style="font-size: 11px; color: #b22222; text-transform: uppercase; font-weight: bold;">WHT Deducted (Tax Credit)</div>
                <div style="font-size: 22px; font-weight: 900; color: #b22222;">- ₦{wht_deducted:,.2f}</div>
            </div>
            <div style="background-color: #e8f5e9; padding: 15px; border-radius: 8px; text-align: center; border: 1px solid #c8e6c9;">
                <div style="font-size: 12px; color: #2e7d32; text-transform: uppercase; font-weight: bold;">Net Payout Expected</div>
                <div style="font-size: 26px; font-weight: 900; color: #2e7d32;">₦{net_payout:,.2f}</div>
            </div>
        </div>
        <div style="text-align: center; padding: 12px; background-color: #f8f9fa; font-size: 10px; color: #888; border-top: 1px solid #eee;">
            VALID FOR RECORD KEEPING • SCREENSHOT TO SHARE 📸
        </div>
    </div>
    """
    return html


# --- 7. MAIN APP UI ---
def main():
    # BRANDING: Pronounced Title, Smaller Subtitle
    st.markdown('<p class="main-title">taX26</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-title">Compliance Suite NG</p>', unsafe_allow_html=True)
    
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
            
            with st.expander("💰 Tax Saver: Voluntary Contributions"):
                st.markdown('<div class="advice-box"><b>Street Smart Tip:</b> Pension and Life Insurance are <b>Tax Free</b>. Instead of paying that money to FIRS, put it in your own future!</div>', unsafe_allow_html=True)
                pension_vol = st.number_input("Add Voluntary Pension (Annual)", 0.0, step=50000.0)
                life_ins = st.number_input("Add Life Insurance Premium", 0.0, step=50000.0)
                nhf = st.number_input("Add NHF Contribution", 0.0, step=20000.0)

            if st.button("Calculate My Tax Liability"):
                tax_new, deductions = calculate_nta_2025_individual(gross, rent, pension_vol, life_ins, nhf)
                tax_old = calculate_pita_2011_individual(gross)
                diff = tax_new - tax_old
                pct_change = ((tax_new - tax_old) / tax_old * 100) if tax_old > 0 else (100 if tax_new > 0 else 0)

                st.divider()
                
                # RENDER HTML CARD
                card_html = render_paye_card_html(tax_old, tax_new, pct_change, gross)
                st.markdown(card_html, unsafe_allow_html=True)
                st.markdown('<div class="screenshot-hint">👆 <b>Long Press</b> or <b>Screenshot</b> this card to share on WhatsApp! 📸</div>', unsafe_allow_html=True)

                if diff < 0:
                    if lottie_celebrate: st_lottie(lottie_celebrate, height=150, key="anim_save")
                
        elif profile == "Freelancer":
            st.info("💡 FIRS taxes **PROFIT**, not Revenue. Deduct your costs first!")
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

    # --- TAB 2: BUSINESS ---
    with tab2:
        st.write("#### Corporate Tax & Salary Planning")
        with st.expander("👔 Director Salary Optimizer"):
            st.markdown('<div class="advice-box"><b>CEO Tip:</b> Don\'t pay yourself a flat salary. Structure it to maximize legal allowances.</div>', unsafe_allow_html=True)
            pkg = st.number_input("Total Monthly Package Target (₦)", 0.0, step=50000.0)
            if pkg > 0:
                basic, house, trans = pkg*0.4, pkg*0.3, pkg*0.2
                util = pkg*0.1
                pen = (basic+house+trans) * 0.08
                st.markdown(f"**Optimal Structure:** Basic: ₦{basic:,.2f} | Housing: ₦{house:,.2f} | Transport: ₦{trans:,.2f} | **Pension:** ₦{pen:,.2f}")
        
        st.divider()
        st.write("**Company Income Tax (CIT) Checker**")
        turn = st.number_input("Annual Turnover", 0.0, step=1000000.0)
        asset = st.number_input("Total Assets", 0.0, step=1000000.0)
        prof = st.number_input("Net Profit", 0.0, step=500000.0)
        is_pro = st.checkbox("Professional Service? (Audit, Legal)")
        
        if st.button("Check CIT Status"):
            cit, dev, status = calculate_corporate_tax(turn, asset, prof, is_pro)
            tot = cit + dev
            st.markdown(f"**Category:** {status}")
            st.metric("Total Tax Liability", f"₦{tot:,.2f}")

    # --- TAB 3: TOOLS ---
    with tab3:
        tool = st.selectbox("Select Tool", ["WHT Invoice Generator", "Japa Calculator (UK/Canada)", "Inflation Checker"])
        
        if tool == "WHT Invoice Generator":
            st.markdown('<div class="advice-box"><b>WHT is Money!</b> Save this certificate as proof.</div>', unsafe_allow_html=True)
            
            # UPDATED COLUMNS FOR VENDOR NAME
            c1, c2 = st.columns(2)
            ven = c1.text_input("Vendor Name (You)")
            cli = c2.text_input("Client Name (Payer)")
            
            c3, c4 = st.columns(2)
            amt = c3.number_input("Invoice Amount", 0.0, step=50000.0)
            typ = c4.selectbox("Type", ["Consultancy/Professional", "Construction", "Supply", "Director Fees", "Dividends"])
            
            tin = st.checkbox("I have a TIN", True)
            
            if st.button("Generate WHT Certificate"):
                w, n, r = calculate_wht(amt, typ, tin)
                # RENDER HTML CARD
                cert_html = render_wht_card_html(ven, cli, amt, w, n)
                st.markdown(cert_html, unsafe_allow_html=True)
                st.markdown('<div class="screenshot-hint">👆 <b>Screenshot</b> this blue card and send it to your client! 📸</div>', unsafe_allow_html=True)

        elif tool == "Japa Calculator (UK/Canada)":
            st.subheader("✈️ Purchasing Power Parity (PPP)")
            ng_sal = st.number_input("Current Nigeria Salary (Annual)", 0.0, step=1000000.0)
            dest = st.selectbox("Moving to:", ["London, UK", "Toronto, Canada"])
            
            if st.button("Compare Lifestyle"):
                if "UK" in dest: curr, fx, ppp = "£", 2150, 0.4
                else: curr, fx, ppp = "CAD$", 1250, 0.45
                equiv = (ng_sal / fx) / ppp
                st.metric(f"Equivalent {curr} Salary Needed", f"{curr}{equiv:,.0f}")
                st.warning(f"To match your **₦{ng_sal:,.0f}** lifestyle in Lagos, you need to earn **{curr}{equiv:,.0f}** abroad.")

        elif tool == "Inflation Checker":
            st.subheader("📉 The 'Sapa' Reality Check")
            sal = st.number_input("Monthly Salary", 0.0, step=50000.0)
            if st.button("Check 2021 Value"):
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
