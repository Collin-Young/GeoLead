#!/usr/bin/env python
import os
import sqlite3
import subprocess
import tempfile
import csv
import json
from flask import Flask, render_template, request, jsonify, send_file

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'

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
    return results

def get_total_records():
    """Get total number of records in database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM data")
    count = cursor.fetchone()[0]
    conn.close()
    return count

@app.route('/')
def index():
    """Main search page"""
    total_records = get_total_records()
    return render_template('index.html', total_records=total_records)

@app.route('/search')
def search():
    """Handle search requests"""
    query = request.args.get('q', '').strip()
    limit = int(request.args.get('limit', 100))
    
    if not query:
        return jsonify({'results': [], 'count': 0, 'query': query})
    
    results = search_database(query, limit)
    
    return jsonify({
        'results': results,
        'count': len(results),
        'query': query
    })

@app.route('/generate_landid', methods=['POST'])
def generate_landid():
    """Generate Land.id link for selected records"""
    data = request.get_json()
    selected_records = data.get('records', [])
    
    if not selected_records:
        return jsonify({'error': 'No records selected'}), 400
    
    # Create temporary CSV file for the automation script
    temp_dir = tempfile.mkdtemp()
    input_file = os.path.join(temp_dir, 'input.csv')
    output_file = os.path.join(temp_dir, 'output.csv')
    
    try:
        # Write CSV file manually
        with open(input_file, 'w') as csvfile:
            fieldnames = ['Reference', 'APN', 'County Name', 'State', 'Owner Mailing Name', 'Offer Price', 'Lot Acreage']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for record in selected_records:
                writer.writerow({
                    'Reference': record.get('Reference', ''),
                    'APN': record.get('APN', ''),
                    'County Name': record.get('County_Name', ''),
                    'State': record.get('State', ''),
                    'Owner Mailing Name': record.get('Owner_Mailing_Name', ''),
                    'Offer Price': record.get('Offer_Price', ''),
                    'Lot Acreage': record.get('Lot_Acreage', '')
                })
        
        return jsonify({
            'message': 'CSV file created. You can now run: python automate_landid.py --input ' + input_file + ' --output ' + output_file,
            'input_file': input_file,
            'output_file': output_file,
            'status': 'ready'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/export_csv', methods=['POST'])
def export_csv():
    """Export selected records to CSV"""
    data = request.get_json()
    selected_records = data.get('records', [])
    
    if not selected_records:
        return jsonify({'error': 'No records selected'}), 400
    
    # Create temporary CSV file
    temp_dir = tempfile.mkdtemp()
    csv_file = os.path.join(temp_dir, 'fop_offers_export.csv')
    
    with open(csv_file, 'w') as csvfile:
        if selected_records:
            fieldnames = selected_records[0].keys()
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for record in selected_records:
                writer.writerow(record)
    
    return send_file(csv_file, as_attachment=True, attachment_filename='fop_offers_export.csv')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)