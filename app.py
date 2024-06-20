import streamlit as st
st.set_page_config(page_title="pyro", page_icon=":bar_chart:", layout="wide")
import pandas as pd
import plotly.express as px
from collections import Counter
import re
from io import BytesIO
import openpyxl
import streamlit_authenticator as stauth
from pathlib import Path
import pickle
import os

names = ["Pranav Alle", "Varaprasad Acharya Devarakonda", "Bharath Raj Saya","Dharmendar Alle", "naveen", "Satya Vuddagiri"]
usernames = ["pranav", "vara", "bharat", "Dharmendar", "userdfz", "Satya"]
#passwords = ["pranav123", "vara123", "bharat123", "Dharmendar123", "dfz@123", "Satya@dfz"]

file_path = Path(__file__).parent / "/Users/saisindhusangavi/Downloads/hashed_pw.pk1"
with file_path.open("rb") as file:
    hashed_passwords = pickle.load(file)

authenticator = stauth.Authenticate(names, usernames, hashed_passwords,
                                    "sales_dashboard", "abcdef")

name, authentication_status, username = authenticator.login("Pyro Analytics Login", "main")

if authentication_status == False:
    st.error("Username/Password is incorrect")

if authentication_status == None:
    st.warning("Please enter your Username and Password")

if authentication_status:

    
    st.title(":bar_chart: PYRO log analysis")
    st.markdown('<style>div.block-container{padding-top:1rem;}</style>', unsafe_allow_html=True)

    def parse_log_file(log_entries):
        """ Parse log entries from uploaded file """
        return log_entries.splitlines()

    def calculate_occurrence_percentage(log_entries, pattern):
        """ Calculate percentage occurrence of a regex pattern in log entries """
        matching_lines = [entry for entry in log_entries if re.search(pattern, entry)]
        total_lines = len(log_entries)
        occurrence_percentage = (len(matching_lines) / total_lines) * 100 if total_lines > 0 else 0
        return occurrence_percentage

    def analyze_failure_reasons_with_imsi(log_entries):
        """ Analyze specific failure reasons in log entries and collect IMSI numbers """
        failures = {
            'Failure: TIMSI status is other than ACTIVE': [],
            'Failure: Rejecting SAI SGSN': [],
            'Failure: NO IMSI FOUND IN DB': []
        }
        for entry in log_entries:
            if 'SAI_RES_FAIL:TIMSI status is other than ACTIVE' in entry:
                imsi = re.search(r'IMSI:(\d+)', entry)
                if imsi:
                    failures['Failure: TIMSI status is other than ACTIVE'].append(imsi.group(1))
            elif 'Rejecting SAI SGSN' in entry:
                imsi = re.search(r'IMSI:(\d+)', entry)
                if imsi:
                    failures['Failure: Rejecting SAI SGSN'].append(imsi.group(1))
            elif 'NO IMSI FOUND IN DB' in entry:
                imsi = re.search(r'IMSI:(\d+)', entry)
                if imsi:
                    failures['Failure: NO IMSI FOUND IN DB'].append(imsi.group(1))
        return failures


    def count_no_imsi_found_entries(log_entries):
        """ Count 'NO IMSI FOUND IN DB' failures and extract IMSI numbers """
        imsi_numbers_counter = Counter()
        for entry in log_entries:
            if 'NO IMSI FOUND IN DB' in entry:
                match = re.search(r'IMSI:(\d+)', entry)
                if match:
                    imsi_number = match.group(1)
                    imsi_numbers_counter[imsi_number] += 1
        return imsi_numbers_counter

    # Function to process log content and count events
    def process_log_content(log_content):
        counters = Counter()
        total_lines = 0

        for line in log_content.splitlines():
            total_lines += 1
            if 'SAI_RES' in line:
                counters['SAI_RES'] += 1
            if 'SRISM_RES' in line:
                counters['SRISM_RES'] += 1
            if 'LU_RES:' in line:
                counters['LU_RES:'] += 1
            if 'ISD_RES:' in line:
                counters['ISD_RES:'] += 1

        return counters, total_lines

    # File uploader
    uploaded_file = st.file_uploader(":file_folder: Upload a log file", type="log")
    if uploaded_file is not None:
        # Read the file and store the contents
        log_content = uploaded_file.getvalue().decode('latin-1')
        log_entries = parse_log_file(log_content)
        
        # Sidebar for analysis options
        st.sidebar.header('Dashboard')
        analysis_option = st.sidebar.radio(
            "Select analysis", 
            ('Occurrence Percentage', 'Failure Reasons', 'Top 5 IMSI Failures', 'Success vs Failure Rate')
        )
        
        if analysis_option == 'Occurrence Percentage':
            pattern = st.sidebar.text_input('Enter pattern to search:', r'SAI_RES_QUIN')
            occurrence_percentage = calculate_occurrence_percentage(log_entries, pattern)
            st.write(f"Occurrence Percentage: {occurrence_percentage:.2f}%")

            event_counters, total_lines = process_log_content(log_content)
        
            # Process the log content
            event_counters, total_lines = process_log_content(log_content)
            
            if total_lines > 0:
                col1, col2 = st.columns(2)  # Create two columns
                with col1:
                    st.subheader("SAI and LU Events")
                    if 'SAI_RES' in event_counters:
                        sai_occurrence = (event_counters['SAI_RES'] / total_lines) * 100
                        st.metric("SAI_RES", f"{event_counters['SAI_RES']} ({sai_occurrence:.2f}%)")
                    if 'LU_RES:' in event_counters:
                        lu_occurrence = (event_counters['LU_RES:'] / total_lines) * 100
                        st.metric("LU_RES:", f"{event_counters['LU_RES:']} ({lu_occurrence:.2f}%)")
                with col2:
                    st.subheader("SRISM and ISD Events")
                    if 'SRISM_RES' in event_counters:
                        srism_occurrence = (event_counters['SRISM_RES'] / total_lines) * 100
                        st.metric("SRISM_RES", f"{event_counters['SRISM_RES']} ({srism_occurrence:.2f}%)")
                    if 'ISD_RES:' in event_counters:
                        isd_occurrence = (event_counters['ISD_RES:'] / total_lines) * 100
                        st.metric("ISD_RES:", f"{event_counters['ISD_RES:']} ({isd_occurrence:.2f}%)")


        elif analysis_option == 'Failure Reasons':
            # Analyze failure reasons and collect IMSI numbers for each type
            failures = analyze_failure_reasons_with_imsi(log_entries)

            # Prepare the failure table with IMSI numbers
            df_failures = pd.DataFrame.from_dict(failures, orient='index').transpose()
            df_failures.fillna("-", inplace=True)  # Replace NaN with dashes for better readability

            # Display pie chart for percentages
            failure_counts = {key: len(values) for key, values in failures.items()}
            failure_labels = list(failure_counts.keys())
            total_entries = len(log_entries)
            failure_sizes = [(count / total_entries) * 100 if total_entries > 0 else 0 for count in failure_counts.values()]
            labels = ['Success'] + failure_labels
            success_occurrence = calculate_occurrence_percentage(log_entries, r'SAI_RES_QUIN')
            sizes = [success_occurrence] + failure_sizes

            data_pie = {
                'Type': labels,
                'Percentage': sizes
            }
            fig_pie = px.pie(data_pie, values='Percentage', names='Type', title='Success vs Failure Rates')
            st.plotly_chart(fig_pie)

            # Display the download button for Excel file
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_failures.to_excel(writer, index=False, sheet_name='Failure Details')

            excel_data = output.getvalue()
            st.download_button(
                label="Download Failure Details as Excel",
                data=excel_data,
                file_name="failure_details.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

            # Display the detailed failure table
            st.write("Detailed Failure Table:")
            st.table(df_failures)




        elif analysis_option == 'Top 5 IMSI Failures':
            imsi_numbers_counter = count_no_imsi_found_entries(log_entries)
            data = {
                'IMSI Number': list(imsi_numbers_counter.keys()),
                'Count': list(imsi_numbers_counter.values())
            }
            df = pd.DataFrame(data)

            # Allow users to select whether to display top 5 or all failures
            display_option = st.selectbox(
                "Display Top 5 or All IMSI Failures?",
                ("Top 5", "All")
            )

            if display_option == "Top 5":
                df = df.sort_values(by='Count', ascending=False).head(5)  # Display only the top 5 IMSI failure counts
            else:
                df = df.sort_values(by='Count', ascending=False)  # Display all IMSI failure counts

            df.reset_index(drop=True, inplace=True)

            # Display bar chart using Plotly Express
            fig_bar = px.bar(df, x='IMSI Number', y='Count', title=f'{display_option} IMSI Failure Counts')
            st.plotly_chart(fig_bar)

            # Display table
            st.write(f"Table of {display_option} IMSI Failure Counts:")
            st.table(df)

            # Pie chart using Plotly Express
            fig_pie = px.pie(df, values='Count', names='IMSI Number', title=f'{display_option} IMSI Failure Counts')
            st.plotly_chart(fig_pie)



        elif analysis_option == 'Success vs Failure Rate':
            # Define success and failure patterns
            success_pattern = r'SAI_RES_QUIN'
            failure_pattern = r'SAI_RES_FAIL'
            
            # Calculate success and failure percentages
            success_percentage = calculate_occurrence_percentage(log_entries, success_pattern)
            failure_percentage = calculate_occurrence_percentage(log_entries, failure_pattern)
            
            # Data for pie chart
            labels = ['Success', 'Failure']
            sizes = [success_percentage, 100 - success_percentage]  # Assuming the rest are failures if not success

            # Plotting the pie chart using Plotly
            data = {
                'Type': labels,
                'Percentage': sizes
            }
            fig = px.pie(data, values='Percentage', names='Type', title='Success vs Failure Rate')
            st.plotly_chart(fig)

    else:
        st.write("No file uploaded yet.")

    authenticator.logout("Logout", "sidebar")
