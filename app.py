import streamlit as st
import requests
from streamlit_lottie import st_lottie
from PIL import Image, ImageDraw, ImageFont
import io
import urllib.parse 

# --- APP CONFIGURATION ---
st.set_page_config(
    page_title="taX26: Nigeria Fiscal Guide",
    page_icon="📉",
    layout="centered",
    initial_sidebar_state="expanded"
)

# --- CUSTOM CSS ---
st.markdown("""
    <style>
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        height: 3em;
        background-color: #008751; 
        color: white;
        font-weight: bold;
    }
    .stButton>button:hover {
        background-color: #006b3f;
        color: white;
    }
    .big-font {
        font-size: 24px !important;
        font-weight: bold;
        color: #333;
    }
    .tax-header {
        font-size: 16px;
        color: #666;
        margin-bottom: -10px;
    }
    </style>
""", unsafe_allow_html=True)

# --- ASSET LOADER (ERROR SAFE) ---
@st.cache_data
def load_lottieurl(url: str):
    try:
        r = requests.get(url, timeout=3)
        if r.status_code != 200: return None
        return r.json()
    except: return None

# Animation URLs
lottie_money = load_lottieurl("https://lottie.host/5a70422c-7a6c-4860-9154-00100780164c/3d6H2k7i4z.json") 
lottie_safe = load_lottieurl("https://lottie.host/98692797-176c-4869-8975-f2d22511475c/7J3f8l5J4z.json")  
lottie_celebrate = load_lottieurl("https://lottie.host/4b85994e-2895-4b07-8840-79873998782d/P7j15j2K4z.json") 

# --- TEXT DICTIONARY ---
TEXT_ASSETS = {
    "English": {
        "title": "taX26 Compliance Suite",
        "tab_personal": "Personal Income",
        "tab_business": "Business / Corporate",
        "tab_tools": "Tools & Invoicing",
        "calc_btn": "Calculate Liability",
        "wht_header": "Withholding Tax Invoice Generator",
        "verdict_save": "Tax Savings Identified",
        "verdict_pay": "Tax Liability Increased",
        "exempt_msg": "Tax Exempt Status",
        "share_msg": "Share Invoice via:"
    },
    "Pidgin": {
        "title": "taX26: The Sapa-Proof Edition 🦁",
        "tab_personal": "Me & My Money",
        "tab_business": "My Hustle / Company",
        "tab_tools": "Vawulence Tools",
        "calc_btn": "Check My Damage 😤",
        "wht_header": "Receipt of Vawulence Generator",
        "verdict_save": "Odogwu! You escaped billing! 🚀",
        "verdict_pay": "Breakfast Served. FIRS is watching. 😭",
        "exempt_msg": "Government Pikin! You are free! 🍼",
        "share_msg": "Show them shege via:"
    }
}

# --- LOGIC CONSTANTS ---
MIN_WAGE_THRESHOLD = 840000 
RENT_RELIEF_CAP = 500000
RENT_RELIEF_RATE = 0.20
PENSION_RATE = 0.08
SMALL_CO_TURNOVER = 50000000
SMALL_CO_ASSETS = 250000000
CIT_RATE = 0.30
DEV_LEVY_RATE = 0.04

# --- CALCULATION ENGINES ---
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
    if gross_income > 100000000: return "TOP 0.1% (BILLIONAIRE STATUS 🦅)"
    if gross_income > 50000000: return "TOP 1% (ODOGWU 🦁)"
    if gross_income > 20000000: return "TOP 5% (CHAIRMAN 🧢)"
    if gross_income > 10000000: return "TOP 10% (BIG BOY 💼)"
    if gross_income > 5000000: return "TOP 20% (SENIOR MAN 👊)"
    return "ASPIRING (THE MASSES ✊)"

# --- IMAGE GENERATOR (SOCIAL MEDIA CARD) ---
def generate_social_card(old_tax, new_tax, pct_change, gross_income, is_incognito=False):
    width, height = 800, 500
    
    # Theme Logic: Red/Orange for Increase, Green for Decrease
    is_increase = new_tax > old_tax
    if is_increase:
        bg_color = "#8B0000" # Dark Red
        accent_color = "#FF4500" # Orange Red
        emoji = "😭"
        title_text = "BREAKFAST SERVED"
    else:
        bg_color = "#006400" # Dark Green
        accent_color = "#32CD32" # Lime Green
        emoji = "🚀"
        title_text = "JUBILATION TIME"

    img = Image.new('RGB', (width, height), color=bg_color)
    d = ImageDraw.Draw(img)
    
    try: 
        font_xl = ImageFont.truetype("arialbd.ttf", 60)
        font_lg = ImageFont.truetype("arialbd.ttf", 40)
        font_md = ImageFont.truetype("arial.ttf", 25)
        font_sm = ImageFont.truetype("arial.ttf", 20)
    except: 
        font_xl = ImageFont.load_default()
        font_lg = ImageFont.load_default()
        font_md = ImageFont.load_default()
        font_sm = ImageFont.load_default()

    # --- DRAWING ---
    # Header
    d.text((width/2, 50), "taX26 REPORT CARD", font=font_md, fill="#FFD700", anchor="mm")
    d.text((width/2, 100), f"{title_text} {emoji}", font=font_xl, fill="white", anchor="mm")
    
    # Percentile (Gamification)
    percentile_msg = get_percentile_text(gross_income)
    d.text((width/2, 150), percentile_msg, font=font_md, fill="#ADD8E6", anchor="mm")

    # Box for Data
    box_x1, box_y1, box_x2, box_y2 = 50, 190, 750, 380
    d.rectangle([box_x1, box_y1, box_x2, box_y2], fill=accent_color, outline="white", width=3)

    if is_incognito:
        # INCOGNITO MODE: Only Percentages
        d.text((width/2, 240), "TAX IMPACT", font=font_lg, fill="white", anchor="mm")
        
        sign = "+" if is_increase else ""
        pct_txt = f"{sign}{pct_change:.1f}%"
        d.text((width/2, 310), pct_txt, font=font_xl, fill="white", anchor="mm")
        d.text((width/2, 350), "(Incognito Mode 🕵️)", font=font_sm, fill="#EEE", anchor="mm")

    else:
        # FULL MODE: Old vs New
        # Old Tax
        d.text((200, 230), "OLD TAX (2011)", font=font_md, fill="#EEE", anchor="mm")
        d.text((200, 270), f"₦{old_tax:,.0f}", font=font_lg, fill="white", anchor="mm")
        
        # Divider Line
        d.line([(400, 210), (400, 360)], fill="white", width=2)
        
        # New Tax
        d.text((600, 230), "NEW TAX (2025)", font=font_md, fill="#EEE", anchor="mm")
        d.text((600, 270), f"₦{new_tax:,.0f}", font=font_lg, fill="white", anchor="mm")
        
        # Pct change at bottom of box
        sign = "+" if is_increase else ""
        d.text((width/2, 340), f"Change: {sign}{pct_change:.1f}%", font=font_md, fill="#FFD700", anchor="mm")

    # Footer
    d.text((width/2, 430), "Powered by taX26", font=font_md, fill="#AAA", anchor="mm")
    d.text((width/2, 460), "Check your own stats at taX26 App", font=font_sm, fill="#888", anchor="mm")

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

# --- MAIN APP UI ---
def main():
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Settings")
        vibe_toggle = st.toggle("Switch to Pidgin English", value=False)
        mode = "Pidgin" if vibe_toggle else "English"
        txt = TEXT_ASSETS[mode]
        st.caption("Toggle to switch between 'Standard English' and 'Pidgin English'.")
    
    st.title(txt['title'])
    
    # Navigation Tabs
    tab1, tab2, tab3 = st.tabs([txt['tab_personal'], txt['tab_business'], txt['tab_tools']])
    
    # --- TAB 1: PERSONAL ---
    with tab1:
        type_choice = st.radio("Select Profile", ["Salary Earner (PAYE)", "Freelancer / Remote", "Diaspora / Japa"], horizontal=True)
        
        if type_choice == "Salary Earner (PAYE)":
            col1, col2 = st.columns(2)
            gross = col1.number_input("Annual Gross Income", min_value=0.0, step=100000.0, format="%.2f")
            rent = col2.number_input("Annual Rent Paid", min_value=0.0, step=50000.0, format="%.2f")
            
            if st.button(txt['calc_btn'], key="btn_paye"):
                tax_new = calculate_nta_2025_individual(gross, rent)
                tax_old = calculate_pita_2011_individual(gross)
                diff = tax_new - tax_old
                
                # Calculate Percentage Increase safely
                if tax_old > 0:
                    pct_change = ((tax_new - tax_old) / tax_old) * 100
                else:
                    pct_change = 100 if tax_new > 0 else 0

                st.divider()

                # --- NEW DISPLAY: NO TRUNCATION ---
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown('<p class="tax-header">Old Tax (2011)</p>', unsafe_allow_html=True)
                    st.markdown(f'<p class="big-font">₦{tax_old:,.2f}</p>', unsafe_allow_html=True)
                with c2:
                    st.markdown('<p class="tax-header">New Tax (2025)</p>', unsafe_allow_html=True)
                    st.markdown(f'<p class="big-font">₦{tax_new:,.2f}</p>', unsafe_allow_html=True)

                # Verdict Message
                if tax_new == 0:
                    if lottie_celebrate: st_lottie(lottie_celebrate, height=150, key="anim_zero")
                    st.success(txt['exempt_msg'])
                elif diff < 0:
                    if lottie_celebrate: st_lottie(lottie_celebrate, height=150, key="anim_save")
                    st.success(f"{txt['verdict_save']} (Saved ₦{abs(diff):,.2f})")
                else:
                    if lottie_money: st_lottie(lottie_money, height=150, key="anim_pay")
                    st.warning(f"{txt['verdict_pay']} (+₦{diff:,.2f})")

                # --- GAMIFICATION / DOWNLOADS ---
                st.write("### 📸 Share Your Tax Vibe")
                
                col_d1, col_d2 = st.columns(2)
                
                # 1. Full Report Card
                full_img = generate_social_card(tax_old, tax_new, pct_change, gross, is_incognito=False)
                col_d1.download_button(
                    label="📥 Download Full Report",
                    data=full_img,
                    file_name="taX26_Full_Report.png",
                    mime="image/png",
                    use_container_width=True
                )
                
                # 2. Incognito Card
                incognito_img = generate_social_card(tax_old, tax_new, pct_change, gross, is_incognito=True)
                col_d2.download_button(
                    label="🕵️ Download Incognito",
                    data=incognito_img,
                    file_name="taX26_Incognito.png",
                    mime="image/png",
                    use_container_width=True
                )
                
                st.image(full_img, caption="Preview of your Full Report Card", use_container_width=True)


        elif type_choice == "Freelancer / Remote":
            st.info("💡 **Tip:** Deduct business expenses (Data, Fuel, Software) before tax.")
            c1, c2 = st.columns(2)
            gross_inc = c1.number_input("Total Earnings", min_value=0.0, step=100000.0)
            expenses = c2.number_input("Total Business Expenses", min_value=0.0, step=50000.0)
            rent = st.number_input("Rent (Personal)", min_value=0.0, step=50000.0)
            
            if st.button(txt['calc_btn'], key="btn_free"):
                tax, profit = calculate_freelancer_tax(gross_inc, expenses, rent)
                st.divider()
                st.metric("Taxable Profit (After Expenses)", f"₦{profit:,.2f}")
                st.metric("Tax Due", f"₦{tax:,.2f}")
                if tax == 0:
                    st.success(txt['exempt_msg'])

        elif type_choice == "Diaspora / Japa":
            days = st.slider("Days spent in Nigeria (Last 12 months)", 0, 365, 30)
            f_inc = st.number_input("Foreign Income (Naira Value)", step=100000.0)
            n_rent = st.number_input("Nigerian Rent Income", step=50000.0)
            n_div = st.number_input("Nigerian Dividends", step=10000.0)
            
            if st.button(txt['calc_btn'], key="btn_diaspora"):
                tax, status, is_safe = calculate_diaspora_tax(days, f_inc, n_rent, n_div)
                st.divider()
                st.subheader(status)
                st.metric("Total Tax Liability", f"₦{tax:,.2f}")
                if is_safe:
                    st.success("Your Foreign Income is SAFE from FIRS.")
                else:
                    st.error("You stayed too long! Global Income is now taxable.")

    # --- TAB 2: BUSINESS ---
    with tab2:
        st.subheader("Corporate Tax Check")
        turnover = st.number_input("Annual Turnover", min_value=0.0, step=1000000.0)
        assets = st.number_input("Total Assets", min_value=0.0, step=1000000.0)
        profit = st.number_input("Assessable Profit", min_value=0.0, step=500000.0)
        is_prof = st.checkbox("Professional Services (Law, Audit, etc)?")
        
        if st.button(txt['calc_btn'], key="btn_corp"):
            cit, dev, status = calculate_corporate_tax(turnover, assets, profit, is_prof)
            total = cit + dev
            st.divider()
            st.markdown(f"**Status:** {status}")
            c1, c2 = st.columns(2)
            c1.metric("CIT", f"₦{cit:,.2f}")
            c2.metric("Dev Levy", f"₦{dev:,.2f}")
            
            if total == 0:
                st.success("Exempt from CIT! Enjoy.")
            else:
                st.warning(f"Total Liability: ₦{total:,.2f}")

    # --- TAB 3: TOOLS (INVOICING) ---
    with tab3:
        st.subheader(txt['wht_header'])
        col1, col2 = st.columns(2)
        client = col1.text_input("Client Name")
        amt = col2.number_input("Invoice Amount", step=50000.0)
        t_type = st.selectbox("Transaction Type", ["Consultancy", "Supply", "Construction"])
        tin = st.checkbox("I have a TIN (Tax ID)", value=True)
        
        if st.button("Generate Invoice Note"):
            wht, net, rate = calculate_wht(amt, t_type, tin)
            st.metric("Net Payout", f"₦{net:,.2f}", delta=f"-₦{wht:,.2f} WHT")

    # --- FOOTER: WHATSAPP ---
    st.write("---") 
    phone_number = "447467395726" 
    message = "Hi, I came from the taX26 app and need assistance."
    encoded_message = urllib.parse.quote(message)
    whatsapp_url = f"https://wa.me/{phone_number}?text={encoded_message}"
    
    st.markdown("### Need Professional Help?")
    st.markdown(f"""
    <div style="display: flex; justify-content: left; margin-bottom: 20px;">
        <a href="{whatsapp_url}" target="_blank" style="text-decoration: none;">
            <button style="
                background-color: #25D366; 
                color: white; 
                border: none; 
                padding: 10px 18px; 
                border-radius: 6px; 
                font-size: 14px; 
                font-weight: bold; 
                cursor: pointer; 
                display: flex; align-items: center; gap: 8px;">
                💬 Chat on WhatsApp
            </button>
        </a>
    </div>
    """, unsafe_allow_html=True)
    
    st.caption("**Webcompliance Limited** - Disclaimer: This tool is for educational purposes only.")

if __name__ == "__main__":
    main()
