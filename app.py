# NEW FUNCTION - Category fetch from dump sheet (FIXED)
def get_category_by_order(order_num):
    try:
        client = get_google_client()
        dump_sheet = client.open_by_key(st.secrets["google_sheets"]["sheet_id"]).worksheet("dump")
        
        # Column E (fleek_id) = 5, Column CL (category) = 90
        order_numbers = dump_sheet.col_values(5)[1:]   # [1:] = Skip header row
        categories = dump_sheet.col_values(90)[1:]      # [1:] = Skip header row
        
        # Order number match karo
        for i, order in enumerate(order_numbers):
            if str(order).strip() == str(order_num).strip():
                if i < len(categories):
                    return categories[i]
                return None
        return None
    except Exception as e:
        st.error(f"Error: {e}")
        return None
