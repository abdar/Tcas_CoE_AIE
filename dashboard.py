from flask import Flask, render_template, jsonify
import pandas as pd
import json
from collections import Counter
import os

app = Flask(__name__)

# Load and process data
def load_data():
    try:
        # Load the data from Excel file
        df = pd.read_excel('tcas_eng_data_cleaned.xlsx')
        print(f"Data loaded successfully. Shape: {df.shape}")
        print(f"Columns: {list(df.columns)}")
        print(f"First few rows:")
        print(df.head())
        return df
    except Exception as e:
        print(f"Error loading data: {e}")
        # Return sample data if file not found
        return create_sample_data()

def create_sample_data():
    # Create sample data based on the provided CSV structure
    data = {
        'มหาวิทยาลัย': ['จุฬาลงกรณ์มหาวิทยาลัย', 'มหาวิทยาลัยเกษตรศาสตร์', 'มหาวิทยาลัยขอนแก่น', 
                      'มหาวิทยาลัยเชียงใหม่', 'มหาวิทยาลัยธรรมศาสตร์'] * 20,
        'ชื่อสาขาวิชา': ['วิศวกรรมคอมพิวเตอร์', 'วิศวกรรมปัญญาประดิษฐ์', 'วิศวกรรมดิจิทัล'] * 33,
        'ประเภทหลักสูตร': ['ภาษาไทย ปกติ', 'นานาชาติ'] * 50,
        'ค่าใช้จ่าย': [25500, 19500, 20000, 23000, 18900, 30000, 25000, 18000, 28000, 50000] * 10
    }
    return pd.DataFrame(data)

# Initialize data
df = load_data()

# Convert 'ค่าใช้จ่าย' to numeric, coercing errors to NaN
if 'ค่าใช้จ่าย' in df.columns:
    df['ค่าใช้จ่าย'] = pd.to_numeric(df['ค่าใช้จ่าย'], errors='coerce')

@app.route('/')
def index():
    return render_template('dashboard.html')

@app.route('/api/stats')
def get_stats():
    # Calculate basic statistics
    total_programs = len(df)
    total_universities = df['มหาวิทยาลัย'].nunique()
    
    # Cost statistics
    if 'ค่าใช้จ่าย' in df.columns:
        cost_data = df['ค่าใช้จ่าย'].dropna()  # Remove NaN values
        max_cost = cost_data.max() if not cost_data.empty else 0
        min_cost = cost_data.min() if not cost_data.empty else 0
    else:
        max_cost = 0
        min_cost = 0
    
    # Program type distribution
    program_types = df['ประเภทหลักสูตร'].value_counts().to_dict()
    
    # Top universities by program count
    uni_counts = df['มหาวิทยาลัย'].value_counts().head(5).to_dict()
    
    # Cost distribution
    cost_ranges = pd.cut(pd.to_numeric(df['ค่าใช้จ่าย'], errors='coerce'), 
                        bins=[0, 20000, 30000, 50000, 100000], 
                        labels=['<20K', '20-30K', '30-50K', '>50K']).value_counts().to_dict()
    
    # University program distribution for progress chart
    university_program_counts = df['มหาวิทยาลัย'].value_counts().to_dict()
    
    return jsonify({
        'total_programs': total_programs,
        'total_universities': total_universities,
        'max_cost': round(max_cost, 0),
        'min_cost': round(min_cost, 0),
        'program_types': program_types,
        'university_counts': uni_counts,
        'cost_ranges': cost_ranges,
        'program_distribution': university_program_counts  # Updated for university distribution
    })

@app.route('/api/chart-data')
def get_chart_data():
    try:
        # Line chart data - Average Cost by University
        if 'มหาวิทยาลัย' in df.columns and 'ค่าใช้จ่าย' in df.columns:
            # Calculate average cost per university
            cost_by_uni = df.groupby('มหาวิทยาลัย')['ค่าใช้จ่าย'].mean().dropna().head(6)
            line_labels = list(cost_by_uni.index)
            line_data = [round(cost, 0) for cost in cost_by_uni.values]
        else:
            line_labels = ['จุฬาลงกรณ์มหาวิทยาลัย', 'มหาวิทยาลัยเกษตรศาสตร์', 'มหาวิทยาลัยขอนแก่น', 
                          'มหาวิทยาลัยสงขลานครินทร์', 'มหาวิทยาลัยมหิดล', 'มหาวิทยาลัยธรรมศาสตร์']
            line_data = [85000, 45000, 25000, 30000, 75000, 55000]
        
        # Bar chart data - top 5 universities by program count
        if 'มหาวิทยาลัย' in df.columns:
            uni_counts = df['มหาวิทยาลัย'].value_counts().head(5)
            bar_labels = list(uni_counts.index)
            bar_data = list(uni_counts.values)
        else:
            bar_labels = ['University 1', 'University 2', 'University 3']
            bar_data = [15, 12, 8]
        
        # Pie chart data - field distribution
        if 'ชื่อสาขาวิชา' in df.columns:
            field_dist = df['ชื่อสาขาวิชา'].value_counts().head(4)
            pie_labels = list(field_dist.index)
            pie_data = list(field_dist.values)
        else:
            pie_labels = ['Computer Engineering', 'AI Engineering', 'Digital Engineering', 'Other Fields']
            pie_data = [45, 25, 20, 10]
        
        return jsonify({
            'line_chart': {
                'labels': line_labels,
                'data': line_data
            },
            'bar_chart': {
                'labels': bar_labels,
                'data': bar_data
            },
            'pie_chart': {
                'labels': pie_labels,
                'data': pie_data
            }
        })
    except Exception as e:
        print(f"Error in get_chart_data: {e}")
        # Return fallback data if there's an error
        return jsonify({
            'line_chart': {
                'labels': ['จุฬาลงกรณ์มหาวิทยาลัย', 'มหาวิทยาลัยเกษตรศาสตร์', 'มหาวิทยาลัยขอนแก่น', 
                          'มหาวิทยาลัยสงขลานครินทร์', 'มหาวิทยาลัยมหิดล', 'มหาวิทยาลัยธรรมศาสตร์'],
                'data': [85000, 45000, 25000, 30000, 75000, 55000]
            },
            'bar_chart': {
                'labels': ['University A', 'University B', 'University C'],
                'data': [15, 12, 8]
            },
            'pie_chart': {
                'labels': ['Computer Engineering', 'AI Engineering', 'Digital Engineering', 'Other Fields'],
                'data': [45, 25, 20, 10]
            }
        })

if __name__ == '__main__':
    app.run(debug=True)