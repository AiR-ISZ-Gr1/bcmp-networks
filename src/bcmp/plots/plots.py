import numpy as np
import datetime as dt
import pandas as pd
import streamlit as st 
import matplotlib.pyplot as plt


def avg_requests_per_class(df):
    def parse_timestamp(ts):
        try:
            minutes, seconds, milliseconds = map(int, ts.split(':'))
            return dt.timedelta(minutes=minutes, seconds=seconds, milliseconds=milliseconds)
        except:
            return np.nan

    df['ts'] = df['ts'].apply(parse_timestamp)

    avg_requests_per_class_server = df.groupby(['source', 'type'])['request_id'].nunique().groupby(level=0).mean()

    results_df = pd.DataFrame({
        'avg_requests_per_class': avg_requests_per_class_server,
    }).reset_index()
    st.write(results_df)
    
    
def procces_time_all_servers(df):
    
    for source in df['source'].unique():
        if "WS" in source:
            data_subset = df[df['source'] == source]
            plot_avg_time_request_server_with_type(data_subset, server_name=source)
            
    
def plot_avg_time_request_server_with_type(data_subset, server_name):
    if not data_subset['ts'].isna().all():
        data_subset['ts'] = pd.to_timedelta(data_subset['ts'])
        data_subset = data_subset.sort_values(by=['request_id', 'ts'])

        processing_intervals = []
        new_request_id = None

        type_color_mapping = {
            "type1": "green",
            "type2": "yellow",
            "type3": "red",
            
        }

        for request_id, group in data_subset.groupby('request_id'):
            group = group.reset_index(drop=True)  #
            last_type = None
            for i, row in group.iterrows():
                if row['action'] == 'received' or (last_type and row.get('type') != last_type):
                    current_type = row.get('type') if row.get('type') else 'initial'
                    new_request_id = f"{request_id}_{i}_{current_type}"
                    
                if row['action'] == 'received':
                    start_time = row['ts']
                    last_type = row['type']
                
                elif row['action'] in ['forwarded', 'rejected']:
                    end_time = row['ts']
                    processing_time = (end_time - start_time).total_seconds()

                    if processing_time > 0:
                        processing_intervals.append({
                            'request_id': new_request_id, 
                            'processing_time': processing_time, 
                            'type': last_type
                        })
                        

                    last_type = row.get('new_type', 'initial')

        processing_intervals_df = pd.DataFrame(processing_intervals)
        if not processing_intervals_df.empty:
            
            processing_intervals_df['new_type'] = processing_intervals_df['type'].map(type_color_mapping)
            average_processing_time_df = processing_intervals_df.groupby(['request_id', 'new_type'])['processing_time'].mean().reset_index()
            
            st.title(f"Average Processing Time for each Request ID with Type ||| {server_name}")

            legend_labels = {
                "red": "Krytyczny",
                "yellow": "Stabilny",
                "green": "Symulant"
            }

            fig, ax = plt.subplots(figsize=(10, 6))
            color = average_processing_time_df['new_type']
            ax.bar(average_processing_time_df['request_id'], average_processing_time_df['processing_time'], color=color)
            ax.set_xlabel('Request ID (with Type)')
            ax.set_ylabel('Average Processing Time (seconds)')
            ax.set_title(f'Average Processing Time for each Request ID with Type ||| {server_name}')

            handles = [
                plt.Line2D([0], [0], marker='o', color=color, label=label, markersize=10, linestyle='None')
                for color, label in legend_labels.items()
            ]
            ax.legend(handles=handles, title="Typy")

            ax.set_xticks([])
            st.pyplot(fig)
        else:
            st.write(f"No valid processing times for source subset.")
    