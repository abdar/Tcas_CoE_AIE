from flask import Flask, render_template, jsonify
import pandas as pd
import json
from collections import Counter
import os

app = Flask(__name__)

# Load and process data
def load_data():
        # Load the data from Excel file
        df = pd.read_excel('data/tcas_eng_data_cleaned.xlsx')
        print(f"Data loaded successfully. Shape: {df.shape}")
        print(f"Columns: {list(df.columns)}")
        print(f"First few rows:")
        print(df.head())
        return df

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
        
        # Find universities with max and min costs
        max_cost_uni = ""
        min_cost_uni = ""
        if not cost_data.empty:
            max_cost_row = df[df['ค่าใช้จ่าย'] == max_cost].iloc[0]
            min_cost_row = df[df['ค่าใช้จ่าย'] == min_cost].iloc[0]
            max_cost_uni = max_cost_row['มหาวิทยาลัย'] if 'มหาวิทยาลัย' in max_cost_row else ""
            min_cost_uni = min_cost_row['มหาวิทยาลัย'] if 'มหาวิทยาลัย' in min_cost_row else ""
    else:
        max_cost = 0
        min_cost = 0
        max_cost_uni = ""
        min_cost_uni = ""
    
    # Program type distribution
    program_types = df['ประเภทหลักสูตร'].value_counts().to_dict()
    
    # Top universities by program count
    uni_counts = df['มหาวิทยาลัย'].value_counts().head(5).to_dict()
    
    
    # University program distribution for progress chart
    university_program_counts = df['มหาวิทยาลัย'].value_counts().to_dict()
    
    # University tuition data for the new progress chart
    university_tuition = {}
    if 'มหาวิทยาลัย' in df.columns and 'ค่าใช้จ่าย' in df.columns:
        # Calculate average tuition per university from real data only
        tuition_by_uni = df.groupby('มหาวิทยาลัย')['ค่าใช้จ่าย'].mean().dropna()
        university_tuition = {uni: round(cost, 0) for uni, cost in tuition_by_uni.items()}
        print(f"University tuition data calculated from real data: {university_tuition}")
    else:
        print("Required columns not found for university tuition calculation")
        # ไม่ใส่ข้อมูล sample - ให้เป็น dict ว่าง
    
    # Most offered fields across universities
    field_counts = {}
    if 'ชื่อสาขาวิชา' in df.columns and 'มหาวิทยาลัย' in df.columns:
        field_counts = df.groupby('ชื่อสาขาวิชา')['มหาวิทยาลัย'].nunique().sort_values(ascending=False).to_dict()
        print(f"Field counts calculated: {field_counts}")
    else:
        print("Required columns not found for field counts calculation")

    # Top 10 universities with the lowest tuition fees
    top_10_lowest_tuition = {}
    if 'มหาวิทยาลัย' in df.columns and 'ค่าใช้จ่าย' in df.columns:
        tuition_by_uni = df.groupby('มหาวิทยาลัย')['ค่าใช้จ่าย'].mean().dropna()
        sorted_tuition = tuition_by_uni.sort_values().head(10)
        top_10_lowest_tuition = {uni: round(cost, 0) for uni, cost in sorted_tuition.items()}
        print(f"Top 10 universities with the lowest tuition fees: {top_10_lowest_tuition}")
    else:
        print("Required columns not found for top 10 lowest tuition fees calculation")

    return jsonify({
        'total_programs': total_programs,
        'total_universities': total_universities,
        'max_cost': round(max_cost, 0),
        'min_cost': round(min_cost, 0),
        'max_cost_university': max_cost_uni,
        'min_cost_university': min_cost_uni,
        'program_types': program_types,
        'university_counts': uni_counts,
        'program_distribution': university_program_counts,  # University distribution
        'university_tuition': university_tuition,  # New tuition data
        'field_counts': field_counts,  # Most offered fields data
        'top_10_lowest_tuition': top_10_lowest_tuition  # New data for top 10 lowest tuition fees
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

@app.route('/api/university-details/<university_name>')
def get_university_details(university_name):
    try:
        # Filter data for the selected university
        university_data = df[df['มหาวิทยาลัย'] == university_name]

        if university_data.empty:
            return jsonify({'error': 'University not found'}), 404

        # Extract details with individual program costs - show all combinations
        program_details = []
        for _, row in university_data.iterrows():
            program_name = row['ชื่อสาขาวิชา']
            program_type = row['ประเภทหลักสูตร'] if 'ประเภทหลักสูตร' in row and pd.notna(row['ประเภทหลักสูตร']) else 'ไม่ระบุ'
            program_course = row['หลักสูตร'] if 'หลักสูตร' in row and pd.notna(row['หลักสูตร']) else 'ไม่ระบุ'
            program_cost = row['ค่าใช้จ่าย'] if pd.notna(row['ค่าใช้จ่าย']) else 'ไม่ระบุ'
            
            program_details.append({
                'name': program_name,
                'type': program_type,
                'course': program_course,
                'cost': round(program_cost, 0) if program_cost != 'ไม่ระบุ' else 'ไม่ระบุ'
            })

        # Overall average tuition for the university
        avg_tuition = university_data['ค่าใช้จ่าย'].mean()

        return jsonify({
            'university': university_name,
            'program_details': program_details,
            'average_tuition': round(avg_tuition, 2) if not pd.isna(avg_tuition) else 'N/A'
        })
    except Exception as e:
        print(f"Error fetching university details: {e}")
        return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    app.run(debug=True)