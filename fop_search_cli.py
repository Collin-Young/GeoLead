#!/usr/bin/env python
import os
import sqlite3
import csv
import tempfile
import subprocess

# Database path
DB_PATH = 'all_fop_offers-2025-06-14.db'

def search_database(query, limit=100):
    """Search the database for records matching the query"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Search across multiple text fields
    search_sql = """
    SELECT Reference, APN, County_Name, State, Owner_First_Name, Owner_Mailing_Name, 
           Offer_Price, Lot_Acreage, Mail_Address, Mail_City, Mail_State, Mail_Zip_Code,
           Legal_Description
    FROM data 
    WHERE Reference LIKE ? 
       OR APN LIKE ?
       OR County_Name LIKE ?
       OR Owner_First_Name LIKE ?
       OR Owner_Mailing_Name LIKE ?
       OR Mail_Address LIKE ?
       OR Mail_City LIKE ?
       OR Legal_Description LIKE ?
    ORDER BY Reference
    LIMIT ?
    """
    
    search_term = "%" + query + "%"
    cursor.execute(search_sql, [search_term] * 8 + [limit])
    
    columns = [description[0] for description in cursor.description]
    results = []
    for row in cursor.fetchall():
        results.append(dict(zip(columns, row)))
    
    conn.close()
    return results, columns

def display_results(results, columns):
    """Display search results in a formatted way"""
    if not results:
        print("No results found.")
        return
    
    print("\nFound {} result(s):".format(len(results)))
    print("=" * 80)
    
    for i, result in enumerate(results, 1):
        print("\n{}. Reference: {}".format(i, result.get('Reference', 'N/A')))
        print("   APN: {}".format(result.get('APN', 'N/A')))
        print("   County: {}, {}".format(result.get('County_Name', 'N/A'), result.get('State', 'N/A')))
        print("   Owner: {}".format(result.get('Owner_Mailing_Name', result.get('Owner_First_Name', 'N/A'))))
        print("   Offer Price: ${}".format(result.get('Offer_Price', 'N/A')))
        print("   Lot Acreage: {} acres".format(result.get('Lot_Acreage', 'N/A')))
        print("   Mail Address: {}".format(result.get('Mail_Address', 'N/A')))
        print("   Mail City: {}, {} {}".format(
            result.get('Mail_City', 'N/A'), 
            result.get('Mail_State', 'N/A'), 
            result.get('Mail_Zip_Code', '')
        ))

def export_to_csv(results, filename):
    """Export results to CSV file"""
    if not results:
        print("No results to export.")
        return
    
    with open(filename, 'w') as csvfile:
        fieldnames = results[0].keys()
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for result in results:
            writer.writerow(result)
    
    print("Results exported to: {}".format(filename))

def create_landid_input(results, filename):
    """Create input file for Land.id automation script"""
    if not results:
        print("No results to process.")
        return
    
    with open(filename, 'w') as csvfile:
        fieldnames = ['Reference', 'APN', 'County Name', 'State', 'Owner Mailing Name', 'Offer Price', 'Lot Acreage']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        for result in results:
            writer.writerow({
                'Reference': result.get('Reference', ''),
                'APN': result.get('APN', ''),
                'County Name': result.get('County_Name', ''),
                'State': result.get('State', ''),
                'Owner Mailing Name': result.get('Owner_Mailing_Name', ''),
                'Offer Price': result.get('Offer_Price', ''),
                'Lot Acreage': result.get('Lot_Acreage', '')
            })
    
    print("Land.id input file created: {}".format(filename))
    return filename

def main():
    print("FOP Offer Database Search Tool")
    print("=" * 40)
    
    # Get total record count
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM data")
    total_records = cursor.fetchone()[0]
    conn.close()
    
    print("Database contains {} total records".format(total_records))
    
    while True:
        print("\nOptions:")
        print("1. Search database")
        print("2. Exit")
        
        choice = input("\nEnter your choice (1-2): ").strip()
        
        if choice == '1':
            query = input("Enter search term: ").strip()
            if not query:
                print("Please enter a search term.")
                continue
            
            limit = input("Enter max results (default 100): ").strip()
            try:
                limit = int(limit) if limit else 100
            except ValueError:
                limit = 100
            
            print("\nSearching for '{}'...".format(query))
            results, columns = search_database(query, limit)
            display_results(results, columns)
            
            if results:
                print("\nWhat would you like to do with these results?")
                print("1. Export to CSV")
                print("2. Create Land.id input file")
                print("3. Run Land.id automation")
                print("4. Back to main menu")
                
                action = input("Enter your choice (1-4): ").strip()
                
                if action == '1':
                    filename = input("Enter CSV filename (default: search_results.csv): ").strip()
                    filename = filename if filename else "search_results.csv"
                    export_to_csv(results, filename)
                
                elif action == '2':
                    filename = input("Enter input filename (default: landid_input.csv): ").strip()
                    filename = filename if filename else "landid_input.csv"
                    create_landid_input(results, filename)
                
                elif action == '3':
                    input_file = create_landid_input(results, "temp_landid_input.csv")
                    output_file = input("Enter output filename (default: landid_output.csv): ").strip()
                    output_file = output_file if output_file else "landid_output.csv"
                    
                    print("Running Land.id automation...")
                    print("Command: python automate_landid.py --input {} --output {}".format(input_file, output_file))
                    
                    try:
                        subprocess.call(['python', 'automate_landid.py', '--input', input_file, '--output', output_file])
                        print("Land.id automation completed. Check {} for results.".format(output_file))
                    except Exception as e:
                        print("Error running automation: {}".format(str(e)))
                        print("You can run manually: python automate_landid.py --input {} --output {}".format(input_file, output_file))
        
        elif choice == '2':
            print("Goodbye!")
            break
        
        else:
            print("Invalid choice. Please try again.")

if __name__ == '__main__':
    main()