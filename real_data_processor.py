import pandas as pd
import json
import numpy as np

def create_real_dashboard_data():
    """Create dashboard data from real ANR database"""
    
    # Path to the Excel file (using the main Input folder)
    excel_path = r"c:\Users\victo\OneDrive\Documentos\Workstation\Projetos\(CSF) Análise Custo Benefício de ANR - WRI\4. Parâmetros médios de MO\Integrated Models Script\Input\ANR_database_30%.xlsx"
    carbon_path = r"c:\Users\victo\OneDrive\Documentos\Workstation\Projetos\(CSF) Análise Custo Benefício de ANR - WRI\4. Parâmetros médios de MO\Integrated Models Script\dashboard\carbon_data.csv"
    
    print("Loading real data from ANR_database_30%.xlsx...")
    print("Loading carbon data from carbon_data.csv...")
    
    # Load all sheets
    model_df = pd.read_excel(excel_path, sheet_name='model_wri')
    cost_df = pd.read_excel(excel_path, sheet_name='cost') 
    benefit_df = pd.read_excel(excel_path, sheet_name='benefit')
    
    # Load carbon data
    carbon_df = pd.read_csv(carbon_path, sep=';', decimal=',')
    
    # Exchange rates - Include all currency variations found in data
    exchange_rates = {
        "USD": 1.0,
        "Real": 0.20,  # 1 Real ≈ 0.20 USD
        "BRL": 0.20,   # BRL is the same as Real
        "Naira": 0.0012  # 1 Naira ≈ 0.0012 USD
    }
    
    models = []
    
    print(f"Processing {len(model_df)} models...")
    
    for _, model_row in model_df.iterrows():
        model_id = int(model_row['model_id'])
        print(f"Processing model {model_id}...")
        
        # Basic model info
        model_info = {
            "id": model_id,
            "country": str(model_row['country']) if pd.notna(model_row['country']) else "Unknown",
            "target_species": str(model_row['target_species']).strip() if pd.notna(model_row['target_species']) else f"Model {model_id}",
            "species": str(model_row['target_species']).strip() if pd.notna(model_row['target_species']) else f"Model {model_id}",  # Keep both for compatibility
            "currency": str(model_row['currency']) if pd.notna(model_row['currency']) else "USD"
        }
        
        # Get costs for this model
        model_costs = cost_df[cost_df['model_ID'] == model_id]
        costs_by_year = {}
        
        for _, cost_row in model_costs.iterrows():
            year = int(cost_row['year'])
            cost_value = float(cost_row['cost_q']) * float(cost_row['cost_p']) if pd.notna(cost_row['cost_q']) and pd.notna(cost_row['cost_p']) else 0
            cost_name = str(cost_row['cost_name']) if pd.notna(cost_row['cost_name']) else "Unknown Cost"
            cost_currency = str(cost_row['currency']) if pd.notna(cost_row['currency']) else model_info["currency"]
            
            # Convert to USD
            cost_value_usd = cost_value * exchange_rates.get(cost_currency, 1.0)
            
            if year not in costs_by_year:
                costs_by_year[year] = {}
            
            if cost_name not in costs_by_year[year]:
                costs_by_year[year][cost_name] = 0
            costs_by_year[year][cost_name] += cost_value_usd
        
        # Get benefits for this model
        model_benefits = benefit_df[benefit_df['model_ID'] == model_id]
        benefits_by_year = {}
        
        for _, benefit_row in model_benefits.iterrows():
            year = int(benefit_row['year'])
            
            if year not in benefits_by_year:
                benefits_by_year[year] = {}
            
            # Process up to 4 NTFP products
            for i in range(1, 5):
                ntfp_name = f'ntfp_name_{i}'
                ntfp_q = f'ntfp_q_{i}'
                ntfp_p = f'ntfp_p_{i}'
                
                if ntfp_name in benefit_row and pd.notna(benefit_row[ntfp_name]):
                    product_name = str(benefit_row[ntfp_name])
                    quantity = float(benefit_row[ntfp_q]) if pd.notna(benefit_row[ntfp_q]) else 0
                    price = float(benefit_row[ntfp_p]) if pd.notna(benefit_row[ntfp_p]) else 0
                    benefit_value_usd = quantity * price * exchange_rates.get(model_info["currency"], 1.0)
                    
                    if product_name not in benefits_by_year[year]:
                        benefits_by_year[year][product_name] = 0
                    benefits_by_year[year][product_name] += benefit_value_usd
        
        # Process carbon data for this model
        model_carbon = carbon_df[carbon_df['model_ID'] == model_id]
        carbon_by_year = {}
        
        for _, carbon_row in model_carbon.iterrows():
            year = int(carbon_row['year'])
            quantity_tC = float(carbon_row['ntfp_q_2']) if pd.notna(carbon_row['ntfp_q_2']) else 0
            price = float(carbon_row['ntfp_p_2']) if pd.notna(carbon_row['ntfp_p_2']) else 0
            
            # Convert tC to tCO2 by multiplying by 3.67
            quantity_tCO2 = quantity_tC * 3.67
            unit = 'tCO2/ha/year'
            
            # Calculate carbon value in USD using tCO2 quantity
            carbon_value_usd = quantity_tCO2 * price
            carbon_by_year[year] = {
                'quantity': quantity_tCO2,
                'price': price, 
                'unit': unit,
                'value': carbon_value_usd
            }
        
        # Create cash flow data with detailed breakdown
        cash_flow = []
        max_year = max(max(costs_by_year.keys()) if costs_by_year else [1], 
                      max(benefits_by_year.keys()) if benefits_by_year else [1],
                      max(carbon_by_year.keys()) if carbon_by_year else [1])
        
        cumulative_cash_flow = 0
        
        for year in range(1, max_year + 1):
            year_costs = costs_by_year.get(year, {})
            year_benefits = benefits_by_year.get(year, {})
            year_carbon = carbon_by_year.get(year, {})
            
            year_total_costs = sum(year_costs.values())
            year_total_benefits = sum(year_benefits.values())
            year_carbon_benefits = year_carbon.get('value', 0) if year_carbon else 0
            year_net = (year_total_benefits + year_carbon_benefits) - year_total_costs  # Include carbon in net calculation
            cumulative_cash_flow += year_net
            
            # Create detailed cost breakdown for tooltip
            cost_details = [{"category": cat, "amount": amt} for cat, amt in year_costs.items() if amt > 0]
            
            # Create detailed benefit breakdown for tooltip
            benefit_details = []
            for product, amount in year_benefits.items():
                if amount > 0:
                    # Try to get unit and price from original benefit data
                    original_benefit = model_benefits[model_benefits['year'] == year]
                    unit = 'kg'  # default
                    price = 10.0  # default
                    
                    if not original_benefit.empty:
                        for i in range(1, 5):
                            ntfp_name = f'ntfp_name_{i}'
                            ntfp_p = f'ntfp_p_{i}'
                            if ntfp_name in original_benefit.columns:
                                benefit_row = original_benefit.iloc[0]
                                if pd.notna(benefit_row[ntfp_name]) and str(benefit_row[ntfp_name]).strip() == product:
                                    if pd.notna(benefit_row[ntfp_p]):
                                        price = float(benefit_row[ntfp_p])
                                    break
                    
                    quantity = amount / price if price > 0 else 0
                    benefit_details.append({
                        "product": product,
                        "quantity": quantity,
                        "unit": unit,
                        "price": price,
                        "value": amount
                    })
            
            # Carbon data for this year
            carbon_details = None
            if year_carbon and year_carbon.get('value', 0) > 0:
                carbon_details = {
                    "quantity": year_carbon['quantity'],
                    "unit": year_carbon['unit'],
                    "price": year_carbon['price'],
                    "value": year_carbon['value']
                }
            
            cash_flow.append({
                "year": year,
                "costs": year_total_costs,
                "benefits": year_total_benefits,
                "carbon": year_carbon_benefits,  # Add carbon as separate field
                "net": year_net,
                "cumulative": cumulative_cash_flow,
                "cost_details": cost_details,
                "benefit_details": benefit_details,
                "carbon_details": carbon_details  # Add carbon details
            })
        
        # Create cost and benefit arrays for charts
        costs = []
        benefits = []
        
        # Aggregate costs by category
        all_cost_categories = set()
        for year_costs in costs_by_year.values():
            all_cost_categories.update(year_costs.keys())
        
        for category in all_cost_categories:
            total_cost = sum(year_costs.get(category, 0) for year_costs in costs_by_year.values())
            if total_cost > 0:
                costs.append({
                    "category": category,
                    "amount": total_cost
                })
        
        # Aggregate benefits by product
        all_benefit_products = set()
        for year_benefits in benefits_by_year.values():
            all_benefit_products.update(year_benefits.keys())
        
        for product in all_benefit_products:
            total_benefit = sum(year_benefits.get(product, 0) for year_benefits in benefits_by_year.values())
            if total_benefit > 0:
                benefits.append({
                    "category": product,
                    "amount": total_benefit
                })
        
        model_info.update({
            "cash_flow": cash_flow,
            "costs": costs,
            "benefits": benefits
        })
        
        models.append(model_info)
        print(f"Model {model_id}: {len(cash_flow)} years, {len(costs)} cost categories, {len(benefits)} benefit products")
    
    # Create the complete dashboard data structure
    dashboard_data = {
        "models": models,
        "exchange_rates": exchange_rates,
        "base_density_percentage": 30
    }
    
    print(f"\nSummary:")
    print(f"- Total models: {len(models)}")
    print(f"- Countries: {set(m['country'] for m in models)}")
    print(f"- Species: {len(set(m['species'] for m in models))} unique")
    
    return dashboard_data

# Generate the real data
if __name__ == "__main__":
    try:
        data = create_real_dashboard_data()
        
        # Save to JSON
        with open('dashboard_data.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ Real dashboard data saved to dashboard_data.json")
        print(f"File size: {len(json.dumps(data))} characters")
        
        # Show sample of first model
        if data['models']:
            sample = data['models'][0]
            print(f"\nSample model {sample['id']}:")
            print(f"- Species: {sample['species']}")
            print(f"- Country: {sample['country']}")
            print(f"- Cash flow years: {len(sample['cash_flow'])}")
            print(f"- Cost categories: {len(sample['costs'])}")
            print(f"- Benefit products: {len(sample['benefits'])}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()