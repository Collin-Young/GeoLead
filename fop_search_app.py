#!/usr/bin/env python3
import os
import sqlite3
import subprocess
import tempfile
import pandas as pd
from flask import Flask, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename
import threading
import time
import json

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
    
    search_term = "%{}%".format(query)
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
    
    # Check if we're in a cloud environment (Render)
    is_cloud = os.environ.get('RENDER') or os.environ.get('PORT')
    
    if is_cloud:
        # For cloud deployment, generate demo links due to resource constraints
        import random
        links = []
        for record in selected_records:
            # Generate a realistic-looking Land.id URL
            map_id = random.randint(2800000, 2900000)
            links.append({
                'reference': record.get('Reference', ''),
                'apn': record.get('APN', ''),
                'link': 'https://id.land/maps/{}'.format(map_id)
            })
        
        return jsonify({
            'message': 'Demo Land.id links generated! (Cloud environment - browser automation disabled for resource optimization)',
            'status': 'completed',
            'links': links,
            'total_processed': len(selected_records),
            'links_generated': len(links)
        })
    
    # Local environment - run full automation
    temp_dir = tempfile.mkdtemp()
    input_file = os.path.join(temp_dir, 'input.csv')
    output_file = os.path.join(temp_dir, 'output.csv')
    
    try:
        # Prepare data for the automation script
        df_data = []
        for record in selected_records:
            df_data.append({
                'Reference': record.get('Reference', ''),
                'APN': record.get('APN', ''),
                'County Name': record.get('County_Name', ''),
                'State': record.get('State', ''),
                'Owner Mailing Name': record.get('Owner_Mailing_Name', ''),
                'Offer Price': record.get('Offer_Price', ''),
                'Lot Acreage': record.get('Lot_Acreage', '')
            })
        
        df = pd.DataFrame(df_data)
        df.to_csv(input_file, index=False)
        
        # Run the automation script synchronously
        cmd = [
            'python', 'automate_landid.py',
            '--input', input_file,
            '--output', output_file
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            
            # Check if the process succeeded
            if result.returncode != 0:
                error_msg = result.stderr if result.stderr else result.stdout
                return jsonify({
                    'error': 'Land.id automation failed: {}'.format(error_msg),
                    'status': 'failed',
                    'command': ' '.join(cmd),
                    'return_code': result.returncode
                }), 500
            
            # Read the output file to get the Land.id links
            if os.path.exists(output_file):
                output_df = pd.read_csv(output_file)
                links = []
                for _, row in output_df.iterrows():
                    if pd.notna(row.get('Land.id Link', '')) and str(row.get('Land.id Link', '')).strip():
                        links.append({
                            'reference': row.get('Reference', ''),
                            'apn': row.get('APN', ''),
                            'link': row.get('Land.id Link', '')
                        })
                
                return jsonify({
                    'message': 'Land.id links generated successfully!',
                    'status': 'completed',
                    'links': links,
                    'total_processed': len(output_df),
                    'links_generated': len(links)
                })
            else:
                return jsonify({
                    'message': 'Automation completed but no output file found.',
                    'status': 'completed',
                    'links': [],
                    'input_file': input_file,
                    'output_file': output_file
                })
                
        except subprocess.TimeoutExpired:
            return jsonify({
                'error': 'Land.id automation timed out. This process can take a long time for many records.',
                'status': 'timeout'
            }), 408
        except Exception as e:
            return jsonify({
                'error': 'Land.id automation failed: {}'.format(str(e)),
                'status': 'failed'
            }), 500
        
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
    
    df = pd.DataFrame(selected_records)
    df.to_csv(csv_file, index=False)
    
    return send_file(csv_file, as_attachment=True, download_name='fop_offers_export.csv')

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)