import streamlit as st
import networkx as nx
import json, os
import graphviz
from bcmp.simulation import simulate
from bcmp.plots import avg_requests_per_class, procces_time_all_servers

import pandas as pd

PATIENT_TYPES = ["Krytyczny", "Stabilny", "Symulant"]
NODE_TYPES = ["Rejestracja", "Poczekalnia", "Badania", "Gabinet lekarski", 
              "Sala przyjęć", "Oddział", "Wejście", "Wyjście"]
SERVER_TYPES = ["FIFO", "LIFO-PR", "PS", "IS"]
COLOR_MAP = {"Krytyczny": "red", "Stabilny": "gold", "Symulant": "forestgreen"}
COLOR_TYPES = {"FIFO":"#B3A254","LIFO-PR":"#8B4C4C","PS":"#4C6E8B","IS":"#4C8B57"}
DEFAULT_LAMBDA = 1.0
DEFAULT_BUFFER_SIZE = 5
DEFAULT_PRIORITY = 1.0
DEFAULT_LAMBDA = 1.0
DEFAULT_BUFFER_SIZE = 5
DEFAULT_PRIORITY = 1.0

def get_default_state():
    """Returns the default network state configuration"""
    default_graph = nx.MultiDiGraph()
    
    # Add all nodes from the default configuration
    nodes = {
        'Rejestracja-SOR': {'id': 1, 'type': 'fifo', 'params': {'buffer_size': 25}, 
                           'process': {pt: {'type': 'exponential', 'params': {'lambda_': 1.0}} for pt in PATIENT_TYPES}},
        'Rejestracja-NiŚOZ': {'id': 5, 'type': 'fifo', 'params': {'buffer_size': 25}, 
                             'process': {pt: {'type': 'exponential', 'params': {'lambda_': 1.0}} for pt in PATIENT_TYPES}},
        'Sala przyjęć': {'id': 8, 'type': 'lifo-pr', 'params': {}, 
                        'process': {pt: {'type': 'exponential', 'params': {'lambda_': 1.0}} for pt in PATIENT_TYPES}},
        'Poczekalnia-SOR': {'id': 9, 'type': 'is', 'params': {}, 
                           'process': {pt: {'type': 'exponential', 'params': {'lambda_': 1.0}} for pt in PATIENT_TYPES}},
        'Poczekalnia-NiŚOZ': {'id': 10, 'type': 'is', 'params': {}, 
                             'process': {pt: {'type': 'exponential', 'params': {'lambda_': 1.0}} for pt in PATIENT_TYPES}},
        'Lekarz SOR': {'id': 11, 'type': 'fifo', 'params': {'buffer_size': 25}, 
                      'process': {pt: {'type': 'exponential', 'params': {'lambda_': 1.0}} for pt in PATIENT_TYPES}},
        'Lekarz NiŚOZ': {'id': 12, 'type': 'fifo', 'params': {'buffer_size': 25}, 
                        'process': {pt: {'type': 'exponential', 'params': {'lambda_': 1.0}} for pt in PATIENT_TYPES}},
        'Diagnostyka': {'id': 13, 'type': 'fifo', 'params': {'buffer_size': 25}, 
                       'process': {pt: {'type': 'exponential', 'params': {'lambda_': 1.0}} for pt in PATIENT_TYPES}},
        'Dom': {'id': 14, 'output': True},
        'Oddział': {'id': 15, 'output': True}
    }
    
    # Add generators
    generators = {
        'Wejście-SOR-Krytyczni': {'id': 2, 'route': {'destination': 1, 'request_type': 'Krytyczny'}, 
                                 'priority': 3.0, 'generate': {'type': 'poisson', 'params': {'lambda_': 1.0}}},
        'Wejście-SOR-Stabilni': {'id': 3, 'route': {'destination': 1, 'request_type': 'Stabilny'}, 
                                'priority': 2.0, 'generate': {'type': 'poisson', 'params': {'lambda_': 1.0}}},
        'Wejście-SOR-Symulanci': {'id': 4, 'route': {'destination': 1, 'request_type': 'Symulant'}, 
                                 'priority': 1.0, 'generate': {'type': 'poisson', 'params': {'lambda_': 1.0}}},
        'Wejście-NiŚOZ-Stabilni': {'id': 6, 'route': {'destination': 5, 'request_type': 'Stabilny'}, 
                                  'priority': 2.0, 'generate': {'type': 'poisson', 'params': {'lambda_': 1.0}}},
        'Wejście-NiŚOZ-Symulanci': {'id': 7, 'route': {'destination': 5, 'request_type': 'Symulant'}, 
                                   'priority': 1.0, 'generate': {'type': 'poisson', 'params': {'lambda_': 1.0}}}
    }
    
    # Add all nodes to the graph
    for node_name, node_data in nodes.items():
        node_type = 'Wyjście' if node_data.get('output', False) else node_name.split('-')[0]
        color = COLOR_TYPES.get(node_data.get('type', '').upper(), None)
        default_graph.add_node(node_name, type=node_type, color=color)
    
    # Add generator nodes to the graph
    for gen_name in generators:
        default_graph.add_node(gen_name, type='Wejście')
        
    # Add all the routing information and edges
    add_default_routes(nodes)
    add_default_edges(default_graph, nodes, generators)
    
    return {
        'graph': default_graph,
        'nodes': nodes,
        'generators': generators,
        'layout': None
    }

def add_default_routes(nodes):
    """Adds the default routing configuration to the nodes"""
    
    # Rejestracja-SOR routes
    nodes['Rejestracja-SOR']['routes'] = {
        'Krytyczny': {'type': 'random', 'routes': [
            {'probability': 1.0, 'destination': 'Sala przyjęć', 'request': 'Krytyczny'},
            {'probability': 0.0, 'destination': 'Rejestracja-SOR', 'request': 'Stabilny'},
            {'probability': 0.0, 'destination': 'Rejestracja-SOR', 'request': 'Symulant'}
        ]},
        'Stabilny': {'type': 'random', 'routes': [
            {'probability': 0.0, 'destination': 'Rejestracja-SOR', 'request': 'Krytyczny'},
            {'probability': 1.0, 'destination': 'Poczekalnia-SOR', 'request': 'Stabilny'},
            {'probability': 0.0, 'destination': 'Rejestracja-SOR', 'request': 'Symulant'}
        ]},
        'Symulant': {'type': 'random', 'routes': [
            {'probability': 0.0, 'destination': 'Rejestracja-SOR', 'request': 'Krytyczny'},
            {'probability': 0.0, 'destination': 'Rejestracja-SOR', 'request': 'Stabilny'},
            {'probability': 1.0, 'destination': 'Rejestracja-NiŚOZ', 'request': 'Symulant'}
        ]}
    }

    # Rejestracja-NiŚOZ routes
    nodes['Rejestracja-NiŚOZ']['routes'] = {
        'Krytyczny': {'type': 'random', 'routes': [
            {'probability': 0.0, 'destination': 'Rejestracja-SOR', 'request': 'Krytyczny'},
            {'probability': 0.0, 'destination': 'Rejestracja-SOR', 'request': 'Stabilny'},
            {'probability': 0.0, 'destination': 'Rejestracja-SOR', 'request': 'Symulant'}
        ]},
        'Stabilny': {'type': 'random', 'routes': [
            {'probability': 0.0, 'destination': 'Rejestracja-SOR', 'request': 'Krytyczny'},
            {'probability': 1.0, 'destination': 'Poczekalnia-NiŚOZ', 'request': 'Stabilny'},
            {'probability': 0.0, 'destination': 'Rejestracja-SOR', 'request': 'Symulant'}
        ]},
        'Symulant': {'type': 'random', 'routes': [
            {'probability': 0.0, 'destination': 'Rejestracja-SOR', 'request': 'Krytyczny'},
            {'probability': 0.0, 'destination': 'Rejestracja-SOR', 'request': 'Stabilny'},
            {'probability': 1.0, 'destination': 'Poczekalnia-NiŚOZ', 'request': 'Symulant'}
        ]}
    }
    
    # Sala przyjęć routes
    nodes['Sala przyjęć']['routes'] = {
        'Krytyczny': {'type': 'random', 'routes': [
            {'probability': 0.95, 'destination': 'Oddział', 'request': 'Krytyczny'},
            {'probability': 0.0, 'destination': 'Rejestracja-SOR', 'request': 'Stabilny'},
            {'probability': 0.05, 'destination': 'Dom', 'request': 'Symulant'}
        ]},
        'Stabilny': {'type': 'random', 'routes': [
            {'probability': 0.0, 'destination': 'Rejestracja-SOR', 'request': 'Krytyczny'},
            {'probability': 0.0, 'destination': 'Rejestracja-SOR', 'request': 'Stabilny'},
            {'probability': 0.0, 'destination': 'Rejestracja-SOR', 'request': 'Symulant'}
        ]},
        'Symulant': {'type': 'random', 'routes': [
            {'probability': 0.0, 'destination': 'Rejestracja-SOR', 'request': 'Krytyczny'},
            {'probability': 0.0, 'destination': 'Rejestracja-SOR', 'request': 'Stabilny'},
            {'probability': 0.0, 'destination': 'Rejestracja-SOR', 'request': 'Symulant'}
        ]}
    }
    
    # Poczekalnia-SOR routes
    nodes['Poczekalnia-SOR']['routes'] = {
        'Krytyczny': {'type': 'random', 'routes': [
            {'probability': 0.0, 'destination': 'Rejestracja-SOR', 'request': 'Krytyczny'},
            {'probability': 0.0, 'destination': 'Rejestracja-SOR', 'request': 'Stabilny'},
            {'probability': 0.0, 'destination': 'Rejestracja-SOR', 'request': 'Symulant'}
        ]},
        'Stabilny': {'type': 'random', 'routes': [
            {'probability': 0.1, 'destination': 'Lekarz SOR', 'request': 'Krytyczny'},
            {'probability': 0.9, 'destination': 'Lekarz SOR', 'request': 'Stabilny'},
            {'probability': 0.0, 'destination': 'Rejestracja-SOR', 'request': 'Symulant'}
        ]},
        'Symulant': {'type': 'random', 'routes': [
            {'probability': 0.0, 'destination': 'Rejestracja-SOR', 'request': 'Krytyczny'},
            {'probability': 0.0, 'destination': 'Rejestracja-SOR', 'request': 'Stabilny'},
            {'probability': 0.0, 'destination': 'Rejestracja-SOR', 'request': 'Symulant'}
        ]}
    }

    # Poczekalnia-NiŚOZ routes
    nodes['Poczekalnia-NiŚOZ']['routes'] = {
        'Krytyczny': {'type': 'random', 'routes': [
            {'probability': 0.0, 'destination': 'Rejestracja-SOR', 'request': 'Krytyczny'},
            {'probability': 0.0, 'destination': 'Rejestracja-SOR', 'request': 'Stabilny'},
            {'probability': 0.0, 'destination': 'Rejestracja-SOR', 'request': 'Symulant'}
        ]},
        'Stabilny': {'type': 'random', 'routes': [
            {'probability': 0.0, 'destination': 'Rejestracja-SOR', 'request': 'Krytyczny'},
            {'probability': 1.0, 'destination': 'Lekarz NiŚOZ', 'request': 'Stabilny'},
            {'probability': 0.0, 'destination': 'Rejestracja-SOR', 'request': 'Symulant'}
        ]},
        'Symulant': {'type': 'random', 'routes': [
            {'probability': 0.0, 'destination': 'Rejestracja-SOR', 'request': 'Krytyczny'},
            {'probability': 0.0, 'destination': 'Rejestracja-SOR', 'request': 'Stabilny'},
            {'probability': 1.0, 'destination': 'Lekarz NiŚOZ', 'request': 'Symulant'}
        ]}
    }
    
    # Complete for Lekarz SOR, Lekarz NiŚOZ, Diagnostyka, Dom, and Oddział
    nodes['Lekarz SOR']['routes'] = {
        'Krytyczny': {'type': 'random', 'routes': [
            {'probability': 0.5, 'destination': 'Sala przyjęć', 'request': 'Krytyczny'},
            {'probability': 0.5, 'destination': 'Diagnostyka', 'request': 'Stabilny'},
            {'probability': 0.0, 'destination': 'Rejestracja-SOR', 'request': 'Symulant'}
        ]},
        'Stabilny': {'type': 'random', 'routes': [
            {'probability': 0.1, 'destination': 'Sala przyjęć', 'request': 'Krytyczny'},
            {'probability': 0.9, 'destination': 'Diagnostyka', 'request': 'Stabilny'},
            {'probability': 0.0, 'destination': 'Rejestracja-SOR', 'request': 'Symulant'}
        ]},
        'Symulant': {'type': 'random', 'routes': [
            {'probability': 0.0, 'destination': 'Rejestracja-SOR', 'request': 'Krytyczny'},
            {'probability': 0.0, 'destination': 'Rejestracja-SOR', 'request': 'Stabilny'},
            {'probability': 1.0, 'destination': 'Dom', 'request': 'Symulant'}
        ]}
    }
    nodes['Diagnostyka']['routes'] = {
    'Krytyczny': {'type': 'random', 'routes': [
        {'probability': 1.0, 'destination': 'Sala przyjęć', 'request': 'Krytyczny'},
        {'probability': 0.0, 'destination': 'Rejestracja-SOR', 'request': 'Stabilny'},
        {'probability': 0.0, 'destination': 'Rejestracja-SOR', 'request': 'Symulant'}
    ]},
    'Stabilny': {'type': 'random', 'routes': [
        {'probability': 0.0, 'destination': 'Rejestracja-SOR', 'request': 'Krytyczny'},
        {'probability': 1.0, 'destination': 'Lekarz SOR', 'request': 'Stabilny'},
        {'probability': 0.0, 'destination': 'Rejestracja-SOR', 'request': 'Symulant'}
    ]},
    'Symulant': {'type': 'random', 'routes': [
        {'probability': 0.0, 'destination': 'Rejestracja-SOR', 'request': 'Krytyczny'},
        {'probability': 0.0, 'destination': 'Rejestracja-SOR', 'request': 'Stabilny'},
        {'probability': 1.0, 'destination': 'Dom', 'request': 'Symulant'}
    ]}
    }

    nodes['Lekarz NiŚOZ']['routes'] = {
        'Krytyczny': {'type': 'random', 'routes': [
            {'probability': 1.0, 'destination': 'Rejestracja-SOR', 'request': 'Krytyczny'},
            {'probability': 0.0, 'destination': 'Rejestracja-SOR', 'request': 'Stabilny'},
            {'probability': 0.0, 'destination': 'Rejestracja-SOR', 'request': 'Symulant'}
        ]},
        'Stabilny': {'type': 'random', 'routes': [
            {'probability': 0.0, 'destination': 'Rejestracja-SOR', 'request': 'Krytyczny'},
            {'probability': 0.2, 'destination': 'Diagnostyka', 'request': 'Stabilny'},
            {'probability': 0.8, 'destination': 'Dom', 'request': 'Symulant'}
        ]},
        'Symulant': {'type': 'random', 'routes': [
            {'probability': 0.0, 'destination': 'Rejestracja-SOR', 'request': 'Krytyczny'},
            {'probability': 0.0, 'destination': 'Rejestracja-SOR', 'request': 'Stabilny'},
            {'probability': 1.0, 'destination': 'Dom', 'request': 'Symulant'}
        ]}
    }

def add_default_edges(graph, nodes, generators):
    """Adds the default edges to the graph based on routing information"""
    # Add edges from routing information
    for node_name, node_data in nodes.items():
        if 'routes' in node_data:
            for patient_type, route_info in node_data['routes'].items():
                for route in route_info['routes']:
                    if route['probability'] > 0:
                        graph.add_edge(
                            node_name,
                            route['destination'],
                            color=COLOR_MAP.get(route['request'], 'black'),
                            label=f"{patient_type} -> {route['request']} ({route['probability']:.1f})"
                        )
    
    # Add edges from generators
    for gen_name, gen_data in generators.items():
        if 'route' in gen_data and gen_data['route']['destination']:
            dest_node = next((name for name, data in nodes.items() 
                            if data['id'] == gen_data['route']['destination']), None)
            if dest_node:
                graph.add_edge(
                    gen_name,
                    dest_node,
                    color=COLOR_MAP.get(gen_data['route']['request_type'], 'black'),
                    label=f"{gen_data['route']['request_type']}"
                )

class NetworkManager:
    def __init__(self, nodes={}):
        if "network_manager" not in st.session_state:
            st.session_state.network_manager = get_default_state()
        self.state = st.session_state.network_manager
        if nodes:
            for node in nodes:
                self.add_node(node)
    
    def clear_session(self):
        """Clears the current session state and reinitializes with an empty network"""
        st.session_state.network_manager = {
            "graph": nx.MultiDiGraph(),
            "nodes": {},
            "generators": {},
            "layout": None
        }
        self.state = st.session_state.network_manager

    
    def add_node(self, node_type, label, **kwargs):
        queue_type = kwargs.get("queue_type")
        if node_type == "Wejście":
            self._add_generator(label, kwargs)
        elif node_type == "Wyjście":
            self._add_output(label)
        else:
            self._add_server(label, node_type, kwargs)
        
        self.state["graph"].add_node(label, type=node_type, color=COLOR_TYPES.get(queue_type))
        self._update_layout()

    def _add_generator(self, label, kwargs):
        self.state["generators"][label] = {
            "id": len(self.state["nodes"]) + 1,
            "route": {},  # Empty route to be filled later
            "priority": kwargs.get("priority", DEFAULT_PRIORITY),
            "generate": {
                "type": "poisson",
                "params": {
                    "lambda_": kwargs.get("type_lambda", DEFAULT_LAMBDA)
                }
            }
        }
        # Add to nodes as well for connection purposes
        self.state["nodes"][label] = {
            "id": len(self.state["nodes"]) + 1,
            "type": "generator",
            "routes": {}
        }

    def set_generator_route(self, generator_label, destination_label, request_type):
        if generator_label in self.state["generators"] and destination_label in self.state["nodes"]:
            destination_id = self.state["nodes"][destination_label]["id"]
            self.state["generators"][generator_label]["route"] = {
                "destination": destination_id,
                "request_type": request_type
            }
            # Add edge to graph for visualization
            self.state["graph"].add_edge(
                generator_label,
                destination_label,
                color=COLOR_MAP.get(request_type, "black"),
                label=f"{request_type}"
            )

    def _add_output(self, label):
        self.state["nodes"][label] = {
            "id": len(self.state["nodes"]) + 1,
            "output": True
        }

    def _add_server(self, label, node_type, kwargs):
        queue_type = kwargs.get("queue_type", "fifo")
        patient_dict = kwargs.get("patient_dict", {})
        processes = {
            key: {"type": "exponential", "params": {"lambda_": value}}
            for key, value in patient_dict.items() if value
        }
        
        self.state["nodes"][label] = {
            "id": len(self.state["nodes"]) + 1,
            "type": queue_type.lower(),
            "params": {"buffer_size": kwargs.get("buffer_size", DEFAULT_BUFFER_SIZE)} if queue_type.lower() == "fifo" else {},
            "process": processes,
            "routes": {}
        }

    def validate_probabilities(self, transformation_probs):
        """Validate that probabilities sum to either 1 or 0 for each patient type"""
        for patient_type, route_info in transformation_probs.items():
            total_prob = sum(route['probability'] for route in route_info['routes'])
            if not ((0.99 <= total_prob <= 1.01) or (-0.001 <= total_prob <= 0.01)):
                return False, f"Probabilities for {patient_type} must sum to either 1 or 0 (current sum: {total_prob:.2f})"
        return True, ""

    def connect_nodes(self, source, transformation_probs):
        # Validate probabilities first
        is_valid, error_message = self.validate_probabilities(transformation_probs)
        if not is_valid:
            st.error(error_message)
            return False

        # Remove existing edges from this source
        edges_to_remove = list(self.state["graph"].out_edges(source, keys=True))
        self.state["graph"].remove_edges_from(edges_to_remove)

        # Store each route with probability and destination
        for patient_type, route_info in transformation_probs.items():
            valid_routes = []
            
            for route in route_info['routes']:
                destination_label = route['destination']
                if destination_label in self.state["nodes"]:
                    destination_id = self.state["nodes"][destination_label]["id"]
                    
                    # Store each valid route with probability and request type
                    valid_routes.append({
                        "probability": route["probability"],
                        "destination": destination_label,
                        "request": route["request"]
                    })
                    if route['probability'] > 0.001:
                        # Improved label for the edge
                        label_text = f"{patient_type} -> {route['request']} ({route['probability']:.1f})"
                        patient_color = route["request"]

                        # Add edge to the graph with detailed label
                        self.state["graph"].add_edge(
                            source,
                            destination_label,
                            color=COLOR_MAP.get(patient_color, "black"),
                            label=label_text
                        )

            # Store valid routes in the node's state for JSON generation
            if valid_routes:
                self.state["nodes"][source]['routes'][patient_type] = {
                    "type": "random",
                    "routes": valid_routes
                }

        
        return True



    def _update_layout(self):
        if not self.state["layout"] or len(self.state["graph"]) != len(self.state["layout"]):
            self.state["layout"] = nx.spring_layout(self.state["graph"], k=1, iterations=50)

    def draw_graph(self):
        if not self.state["graph"].nodes():
            return

        # Create a new Graphviz object
        dot = graphviz.Digraph()
        dot.attr(rankdir='LR')
        
        # Set default node attributes
        dot.attr('node', shape='rectangle', style='filled', fontname='Arial', width='1.5', height='0.6')
        
        # Add nodes
        for node in self.state["graph"].nodes(data=True):
            dot.node(node[0], node[0], fillcolor=node[1].get('color'))
        
        # Add edges with proper formatting
        for source, target, data in self.state["graph"].edges(data=True):
            color = data.get("color", "black")
            label = data.get("label", "")
            
            # Convert color names to hex codes for better visibility
            color_map = {
                "red": "#FF0000",
                "forestgreen": "#228B22",
                "gold": "#FFD700",
                "black": "#000000"
            }
            edge_color = color_map.get(color, color)
            
            dot.edge(source, target, label=label, color=edge_color, fontcolor=edge_color, penwidth='2')

        
        return dot



    def generate_json(self):
        generators = []
        for gen_label, gen_data in self.state["generators"].items():
            generator = {
                "id": gen_data["id"],
                "route": {},
                "priority": gen_data["priority"],
                "generate": gen_data["generate"]
            }
            
            # Convert destination label to ID for generator route
            if gen_data["route"]:
                dest_label = next((node_label for node_label, node in self.state["nodes"].items() 
                                if node["id"] == gen_data["route"]["destination"]), None)
                if dest_label and not all(str(x) in dest_label for x in ["Oddział","Dom","Wyjście" ] ):
                    generator["route"] = {
                        "destination": gen_data["route"]["destination"],
                        "request_type": gen_data["route"]["request_type"]
                    }
                else:
                    generator["route"] = {
                        "destination": None,
                        "request_type": None
                    }
            
            generators.append(generator)

        # Process server nodes for JSON format
        servers = []
        for server_label, server in self.state["nodes"].items():
            if not server.get("output") and server.get("type") != "generator":
                cleaned_routes = {}
                # Process each patient type's routes
                for ptype, route_data in server.get("routes", {}).items():
                    if route_data["routes"]:
                        cleaned_routes[ptype] = {
                            "type": "random",
                            "routes": []
                        }
                        
                        # Convert destination labels to IDs for each route
                        for route in route_data["routes"]:
                            dest_label = route["destination"]
                            if "Dom" in dest_label or "Oddział" in dest_label:
                                # Set destination and request to null for exit nodes
                                cleaned_route = {
                                    "probability": route["probability"],
                                    "destination": None,
                                    "request_type": None
                                }
                            else:
                                dest_id = self.state["nodes"][dest_label]["id"]
                                cleaned_route = {
                                    "probability": route["probability"],
                                    "destination": dest_id,
                                    "request_type": route["request"]
                                }
                            cleaned_routes[ptype]["routes"].append(cleaned_route)

                # Only include patient type if it has valid routes
                server_copy = server.copy()
                server_copy["routes"] = cleaned_routes
                servers.append(server_copy)

        return {
            "servers": servers,
            "generators": generators
        }
    
def display_legend():
    """Display the server type legend as a row of labels."""
    st.subheader("Server Types Legend")
    
    legend_items = ""
    for server_type, color in COLOR_TYPES.items():
        legend_items += f"<span style='background-color:{color}; padding:5px 10px; " \
                        f"border-radius:5px; color:white; display:inline-block; margin-right:10px;'>" \
                        f"{server_type}</span>"
    
    st.markdown(legend_items, unsafe_allow_html=True)


def main():
    
    analitycs = False
    st.title("Network Graph Builder")
    
    # Add clear session button at the top
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("Clear Session"):
            network = NetworkManager()
            network.clear_session()
            st.rerun()
    
    network = NetworkManager()
    
    # Sidebar for node creation
    with st.sidebar:
        st.header("Node Controls")
        col1, col2 = st.columns(2)
        
        with col1:
            node_type = st.selectbox("Node Type", NODE_TYPES)
            node_label = st.text_input("Label", value=f"{node_type}-{len(network.state['nodes']) + 1}")

        if node_type == "Wejście":
            with col2:
                patient_type = st.selectbox("Patient Type", PATIENT_TYPES)
                patient_lambda = st.number_input("Lambda", 0.1, 10.0, DEFAULT_LAMBDA)
                priority = st.number_input("Priority", 1.0, 5.0, DEFAULT_PRIORITY)
                
                # Add destination selection for generator
                available_destinations = list(network.state["nodes"].keys())
                if available_destinations:
                    destination = st.selectbox("Initial Destination", available_destinations)
                    if st.button("Add Node and Connect"):
                        network.add_node(node_type, node_label, patient_type=patient_type,
                                      type_lambda=patient_lambda, priority=priority)
                        network.set_generator_route(node_label, destination, patient_type)
                else:
                    if st.button("Add Node"):
                        network.add_node(node_type, node_label, patient_type=patient_type,
                                      type_lambda=patient_lambda, priority=priority)

        elif node_type != "Wyjście":
            with col2:
                server_type = st.selectbox("Server Type", SERVER_TYPES)
                if server_type == "FIFO":
                    buffer_size = st.number_input("Buffer Size", 1, 100, DEFAULT_BUFFER_SIZE)
                
                lambdas = {
                    ptype: st.number_input(f"Lambda for {ptype}", 0.1, 10.0, DEFAULT_LAMBDA)
                    for ptype in PATIENT_TYPES
                }

                if st.button("Add Node"):
                    network.add_node(node_type, node_label, queue_type=server_type,
                                   buffer_size=buffer_size if server_type == "FIFO" else None,
                                   patient_dict=lambdas)
        else:
            if st.button("Add Node"):
                network.add_node(node_type, node_label)

        # Node connection controls
        st.header("Connect Nodes")
        source = st.selectbox("Source", list(network.state["nodes"].keys()), key="source")
        
        if source:
            st.write("Configure routes for each patient type:")
            transformation_probs = {}
            
            # Create tabs for each patient type
            tabs = st.tabs(PATIENT_TYPES)
            for i, ptype in enumerate(PATIENT_TYPES):
                with tabs[i]:
                    transformation_probs[ptype] = {"type": "random", "routes": []}
                    probs = []
                    dests = []
                    
                    for target_type in PATIENT_TYPES:
                        col1, col2 = st.columns(2)
                        with col1:
                            prob = st.number_input(f"Probability for {target_type}", 
                                                0.0, 1.0, 0.0, 0.1,
                                                key=f"prob_{source}_{ptype}_{target_type}")
                            probs.append(prob)
                        with col2:
                            dest = st.selectbox(f"Destination for {target_type}",
                                            list(network.state["nodes"].keys()),
                                            key=f"dest_{source}_{ptype}_{target_type}")
                            dests.append(dest)
                    
                    total_prob = sum(probs)
                    st.write(f"Total probability: {total_prob:.2f}")
                    if not ((0.99 <= total_prob <= 1.01) or (0 <= total_prob <=0.01)):
                        st.warning("Total probability must equal 1.0")
                    
                    for prob, dest, target_type in zip(probs, dests, PATIENT_TYPES):
                        transformation_probs[ptype]['routes'].append({
                            "probability": prob,
                            "destination": dest,
                            "request": target_type
                        })

            if st.button("Connect"):
                network.connect_nodes(source, transformation_probs)


    dot = network.draw_graph()
    if dot:
        st.graphviz_chart(dot)

    col1, col2 = st.columns(2)
    with col2:
        time = st.number_input(f"Time for simulation", 
                                                5, 120, 30, 5,
                                                key=f"sim_time")
    with col1:
        if st.button("Simulate"):
            json_data = network.generate_json()
            # st.json(json_data)
            json_str = json.dumps(json_data, indent=2)
            # st.download_button("Download JSON", data=json_str, 
            #                   file_name="network.json", mime="application/json")
            path = "configs/networks/network.json"
            with open(path,"w") as file:
                file.write(json_str)

            sim_id = simulate(path,duration=time)
            
            # print(sim_id)
            json_link = f"logs/{sim_id}.jsonl"
            data_visual = pd.read_json(json_link, lines=True)
            analitycs = True
            
            
            # procces_time_all_servers(data_visual)
            
            # os.remove(path)
    display_legend()
    if analitycs:
        avg_requests_per_class(data_visual)
        procces_time_all_servers(data_visual)

    # print(network.state)
                

        

if __name__ == "__main__":
    main()
