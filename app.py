import streamlit as st
import networkx as nx
from pyvis.network import Network
import streamlit.components.v1 as components
import json
import tempfile

NODE_COLORS = {
    "activation": "#8BC34A",
    "inhibition": "#F44336",
    "neutral": "#2196F3",
}
EDGE_COLORS = {
    "activation": "green",
    "inhibition": "red",
    "neutral": "gray",
}

def create_sample_pathway():
    G = nx.DiGraph()
    G.add_node("EGFR", title="Epidermal Growth Factor Receptor", state="activation",
               description="Receptor that binds growth factors.")
    G.add_node("GRB2", title="Growth factor receptor-bound protein 2", state="activation",
               description="Adapter protein that links receptors to SOS.")
    G.add_node("SOS", title="Son of Sevenless", state="activation",
               description="Activates RAS.")
    G.add_node("RAS", title="RAS protein", state="neutral",
               description="Small GTPase involved in cell signaling.")
    G.add_node("RAF", title="RAF kinase", state="neutral",
               description="Kinase activated by RAS.")
    G.add_node("MEK", title="MEK kinase", state="neutral",
               description="Phosphorylates ERK.")
    G.add_node("ERK", title="ERK kinase", state="neutral",
               description="Regulates transcription factors.")
    
    G.add_edge("EGFR", "GRB2", title="binds to", state="activation",
               description="EGFR activates GRB2 by binding.")
    G.add_edge("GRB2", "SOS", title="activates", state="activation",
               description="GRB2 recruits SOS to membrane.")
    G.add_edge("SOS", "RAS", title="activates", state="activation",
               description="SOS activates RAS by exchanging GDP for GTP.")
    G.add_edge("RAS", "RAF", title="activates", state="activation",
               description="RAS activates RAF.")
    G.add_edge("RAF", "MEK", title="phosphorylates", state="activation",
               description="RAF phosphorylates MEK.")
    G.add_edge("MEK", "ERK", title="phosphorylates", state="activation",
               description="MEK phosphorylates ERK.")
    G.add_edge("ERK", "EGFR", title="feedback inhibition", state="inhibition",
               description="ERK inhibits EGFR via feedback.")
    return G

def draw_graph_with_controls(G, show_activation, show_inhibition, animation_speed_ms, paused):
    net = Network(height="650px", width="100%", directed=True, notebook=False)

    for node, data in G.nodes(data=True):
        color = NODE_COLORS.get(data.get("state", "neutral"), NODE_COLORS["neutral"])
        net.add_node(node, label=node, title=data.get("title", ""), color=color)

    for src, tgt, data in G.edges(data=True):
        state = data.get("state", "neutral")
        if state == "activation" and not show_activation:
            continue
        if state == "inhibition" and not show_inhibition:
            continue
        color = EDGE_COLORS.get(state, EDGE_COLORS["neutral"])
        net.add_edge(src, tgt, title=data.get("title", ""), color=color, arrows="to")

    # JSON only options for pyvis
    options_json = """
    {
      "nodes": {
        "font": {"size": 16, "face": "Arial"}
      },
      "edges": {
        "font": {"align": "top"},
        "arrows": {"to": {"enabled": true}}
      },
      "physics": {
        "enabled": true,
        "barnesHut": {"gravitationalConstant": -30000, "springLength": 250},
        "minVelocity": 0.75
      },
      "manipulation": false
    }
    """
    net.set_options(options_json)

    # Save to temp file
    temp_html_path = tempfile.NamedTemporaryFile(suffix=".html", delete=False).name
    net.save_graph(temp_html_path)

    # Read and inject JS animation script before </body>
    with open(temp_html_path, "r", encoding="utf-8") as f:
        html = f.read()

    # JavaScript for animation with pause and speed control
    # Assumes network variable is global (pyvis uses 'network')
    animation_js = f"""
<script>
  var animationSpeed = {animation_speed_ms};
  var isPaused = {str(paused).lower()};

  function animateSignal() {{
    var nodes = network.body.data.nodes.getIds();
    var edges = network.body.data.edges.getIds();
    var all = nodes.concat(edges);
    var index = 0;

    function highlight() {{
      if (isPaused) {{
        return;
      }}
      // Reset colors to original by removing 'color' attribute override
      nodes.forEach(function(nodeId) {{
        network.body.data.nodes.update({{id: nodeId, color: undefined}});
      }});
      edges.forEach(function(edgeId) {{
        network.body.data.edges.update({{id: edgeId, color: undefined}});
      }});

      var id = all[index];
      if (nodes.includes(id)) {{
        network.body.data.nodes.update({{id: id, color: 'orange'}});
      }} else {{
        network.body.data.edges.update({{id: id, color: 'orange'}});
      }}
      index = (index + 1) % all.length;
    }}

    setInterval(highlight, animationSpeed);
  }}

  network.once('afterDrawing', function() {{
    animateSignal();
  }});
</script>
"""

    # Insert animation JS before </body>
    html = html.replace("</body>", animation_js + "</body>")

    components.html(html, height=700)

def node_edge_info_panel(G):
    st.markdown("### Select a node or edge to see detailed info")

    node = st.selectbox("Node", options=[""] + list(G.nodes))
    if node:
        st.markdown(f"**Node:** {node}")
        st.write(G.nodes[node].get("description", "No description available."))

    edges = list(G.edges(data=True))
    edge_labels = [f"{src} -> {tgt}" for src, tgt, _ in edges]
    edge_sel = st.selectbox("Edge", options=[""] + edge_labels)
    if edge_sel:
        idx = edge_labels.index(edge_sel)
        src, tgt, data = edges[idx]
        st.markdown(f"**Edge:** {src} → {tgt}")
        st.write(data.get("description", "No description available."))

# --- Streamlit UI ---
st.title("Cell Signaling Pathway Visualizer with Animation Controls")

st.sidebar.header("Edge Visibility Filters")
show_activation = st.sidebar.checkbox("Show Activation Edges", value=True)
show_inhibition = st.sidebar.checkbox("Show Inhibition Edges", value=True)

st.sidebar.header("Animation Controls")
animation_speed_ms = st.sidebar.slider("Animation Speed (ms per highlight)", 200, 3000, 1000, step=100)
paused = st.sidebar.checkbox("Pause Animation", value=False)

uploaded_file = st.file_uploader("Upload pathway JSON file with 'state' and 'description'", type=["json"])

if uploaded_file:
    try:
        data = json.load(uploaded_file)
        G = nx.DiGraph()
        for node in data.get("nodes", []):
            G.add_node(node["id"], title=node.get("title", node["id"]),
                       state=node.get("state", "neutral"),
                       description=node.get("description", "No description."))
        for edge in data.get("edges", []):
            G.add_edge(edge["source"], edge["target"], title=edge.get("title", ""),
                       state=edge.get("state", "neutral"),
                       description=edge.get("description", "No description."))
        st.success("Custom pathway loaded successfully!")
    except Exception as e:
        st.error(f"Error loading file: {e}")
        G = create_sample_pathway()
else:
    G = create_sample_pathway()

draw_graph_with_controls(G, show_activation, show_inhibition, animation_speed_ms, paused)
node_edge_info_panel(G)
