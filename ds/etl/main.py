"""
ETL Service — Campaign Optimization Engine
Loads customer features from UCI Online Retail II dataset,
engineers RFM + behavioral features, inserts into PostgreSQL.
"""
import os

def main():
    print("ETL service started.")
    # TODO (M2): Feature engineering pipeline
    # 1. Load UCI Online Retail II data
    # 2. Compute RFM features per customer
    # 3. Compute basket_diversity, avg_order_size, purchase_regularity
    # 4. Insert into customers table
    print("ETL service placeholder — implement in M2.")

if __name__ == "__main__":
    main()
