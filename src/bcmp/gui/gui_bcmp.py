import streamlit as st
import json
import os

if "filename" not in st.session_state:
    st.session_state["filename"] = "configuration.json"  # Default filename

def generate_configuration(servers, generators):
    config = {
        "servers": servers,
        "generators": generators
    }
    return config

st.sidebar.title("Configuration Settings")
st.sidebar.text_input("Output Filename", value="configuration.json", key="filename")

st.sidebar.title("Server Configuration")
servers = []
num_servers = st.sidebar.number_input("Number of Servers", min_value=1, max_value=10, step=1)

for i in range(num_servers):
    st.sidebar.subheader(f"Server {i + 1}")
    server_id = st.sidebar.number_input(f"Server {i + 1} ID", min_value=1)
    server_type = st.sidebar.selectbox(f"Server {i + 1} Type", ["fifo", "lifo-pr", "ps", "is"], key=f"type_{i}")
    buffer_size = st.sidebar.number_input(f"Buffer Size for Server {i + 1}", min_value=0, value=5, key=f"buffer_{i}")

    processes = {}
    for req_type in ["type1", "type2", "type3"]:
        process_type = st.sidebar.selectbox(f"Process Type for {req_type} in Server {i + 1}", ["exponential", "poisson"], key=f"process_{req_type}_{i}")
        lambda_ = st.sidebar.number_input(f"Lambda for {req_type} in Server {i + 1}", min_value=0.1, value=1.0, step=0.1, key=f"lambda_{req_type}_{i}")
        processes[req_type] = {
            "type": process_type,
            "params": {
                "lambda_": lambda_
            }
        }

    routes = {}
    for req_type in ["type1", "type2", "type3"]:
        route_type = st.sidebar.selectbox(f"Route Type for {req_type} in Server {i + 1}", ["random", "round_robin"], key=f"route_{req_type}_{i}")
        num_routes = st.sidebar.number_input(f"Number of Routes for {req_type} in Server {i + 1}", min_value=1, max_value=5, step=1, key=f"num_routes_{req_type}_{i}")
        route_list = []
        for j in range(num_routes):
            destination = st.sidebar.number_input(f"Destination for Route {j + 1} of {req_type} in Server {i + 1}", min_value=1, key=f"dest_{req_type}_{i}_{j}")
            request_type = st.sidebar.selectbox(f"Request Type for Route {j + 1} of {req_type} in Server {i + 1}", ["type1", "type2", "type3"], key=f"req_{req_type}_{i}_{j}")
            probability = st.sidebar.slider(f"Probability for Route {j + 1} of {req_type} in Server {i + 1}", min_value=0.0, max_value=1.0, step=0.1, key=f"prob_{req_type}_{i}_{j}")
            route_list.append({
                "destination": destination,
                "request_type": request_type,
                "probability": probability
            })
        routes[req_type] = {
            "type": route_type,
            "routes": route_list
        }

    servers.append({
        "id": server_id,
        "type": server_type,
        "params": {"buffer_size": buffer_size},
        "process": processes,
        "routes": routes
    })

st.sidebar.title("Generator Configuration")
generators = []
num_generators = st.sidebar.number_input("Number of Generators", min_value=0, max_value=10, step=1)

for i in range(num_generators):
    st.sidebar.subheader(f"Generator {i + 1}")
    generator_id = st.sidebar.number_input(f"Generator {i + 1} ID", min_value=1, key=f"gen_id_{i}")
    destination = st.sidebar.number_input(f"Destination for Generator {i + 1}", min_value=1, key=f"gen_dest_{i}")
    request_type = st.sidebar.selectbox(f"Request Type for Generator {i + 1}", ["type1", "type2", "type3"], key=f"gen_req_{i}")
    priority = st.sidebar.number_input(f"Priority for Generator {i + 1}", min_value=1, key=f"gen_priority_{i}")
    generate_type = st.sidebar.selectbox(f"Generate Type for Generator {i + 1}", ["poisson", "exponential"], key=f"gen_type_{i}")
    gen_lambda = st.sidebar.number_input(f"Lambda for Generator {i + 1}", min_value=0.1, value=0.5, step=0.1, key=f"gen_lambda_{i}")
    
    generators.append({
        "id": generator_id,
        "route": {"destination": destination, "request_type": request_type},
        "priority": priority,
        "generate": {
            "type": generate_type,
            "params": {"lambda_": gen_lambda}
        }
    })

st.write("### Generated Configuration JSON")
config = generate_configuration(servers, generators)
st.json(config)

current_directory = os.path.dirname(os.path.abspath(__file__))
filename = st.session_state["filename"]
file_path = os.path.join(current_directory, filename)
with open(file_path, "w") as f:
    json.dump(config, f, indent=4)

st.write(f"Configuration saved to `{filename}` in the current directory.")
