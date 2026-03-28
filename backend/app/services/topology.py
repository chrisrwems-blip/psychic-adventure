"""System topology builder — constructs the electrical distribution tree from SLD text.

Builds a directed graph of what feeds what:
  UTILITY → E6.2H 4000A (Source A Q7)
    ├─ E4.2H 3200A (IT Coupler MBB Q13)
    ├─ XT7H 1000A (UPS UIB A Q9)
    │   └─ XT7H 1000A (UPS Output UOA Q23)
    │       ├─ XT2H 125A (Rack Plug Q14A-H) × 8
    │       └─ XT5H 400A (Network DB Q22)
    ├─ XT7H 1000A (Mech UPS Q3)
    └─ XT7H 800A (Chiller 1 Q10)

Used for:
- Fault current cascade validation
- Selective coordination checks
- Bus rating vs breaker rating
- Upstream/downstream relationship awareness
"""
import re
from dataclasses import dataclass, field
from typing import Optional

from .equipment_extractor import ExtractedEquipment
from .engineering_tables import transformer_secondary_fault_current


@dataclass
class TopologyNode:
    equipment_id: str          # designation from ExtractedEquipment
    equipment_type: str        # breaker, panel, transformer, etc.
    description: str           # human-readable (e.g., "Source A Incomer")
    voltage: Optional[int] = None
    amperage: Optional[int] = None
    interrupting_kA: Optional[int] = None
    page_number: int = 0
    upstream_id: Optional[str] = None
    downstream_ids: list = field(default_factory=list)
    available_fault_current_kA: Optional[float] = None


@dataclass
class SystemTopology:
    nodes: dict  # str -> TopologyNode, keyed by equipment_id
    root_nodes: list  # equipment_ids with no upstream (service entrance)
    relationships: list  # list of (upstream_id, downstream_id, page) tuples

    def get_node(self, equipment_id: str) -> Optional[TopologyNode]:
        return self.nodes.get(equipment_id)

    def get_upstream_chain(self, equipment_id: str) -> list:
        """Walk up the tree and return ordered list from root to this node."""
        chain = []
        current = equipment_id
        visited = set()
        while current and current not in visited:
            visited.add(current)
            node = self.nodes.get(current)
            if not node:
                break
            chain.append(node)
            current = node.upstream_id
        chain.reverse()
        return chain

    def get_downstream_tree(self, equipment_id: str) -> list:
        """Walk down the tree and return all downstream nodes."""
        result = []
        node = self.nodes.get(equipment_id)
        if not node:
            return result
        for child_id in node.downstream_ids:
            child = self.nodes.get(child_id)
            if child:
                result.append(child)
                result.extend(self.get_downstream_tree(child_id))
        return result

    def get_breaker_pairs(self) -> list:
        """Get all upstream-downstream breaker pairs for coordination checks."""
        pairs = []
        for node_id, node in self.nodes.items():
            if node.equipment_type != "breaker":
                continue
            for child_id in node.downstream_ids:
                child = self.nodes.get(child_id)
                if child and child.equipment_type == "breaker":
                    pairs.append((node, child))
        return pairs


def build_topology(equipment: list[ExtractedEquipment], pages: list[dict]) -> SystemTopology:
    """Build the system topology from extracted equipment and SLD page text.

    Strategy:
    1. Create a node for every extracted equipment item
    2. Extract relationships from SLD pages (INCOMING/OUTGOING patterns)
    3. Infer relationships from panel schedule headers (FED FROM)
    4. Infer bus → breaker hierarchy from page proximity
    5. Propagate fault current down through transformers
    """
    nodes = {}
    relationships = []

    # Step 1: Create nodes for all equipment
    for eq in equipment:
        amp_val = _parse_amps(eq.amperage or eq.trip_rating or eq.frame_size)
        ir_val = _parse_kA(eq.interrupting_rating)
        volt_val = _parse_voltage(eq.voltage)

        node = TopologyNode(
            equipment_id=eq.designation,
            equipment_type=eq.equipment_type,
            description=eq.raw_text[:80] if eq.raw_text else eq.designation,
            voltage=volt_val,
            amperage=amp_val,
            interrupting_kA=ir_val,
            page_number=eq.page_number,
        )
        nodes[eq.designation] = node

    # Step 2: Extract relationships from SLD pages
    sld_pages = [p for p in pages if p.get("page_type") == "single_line_diagram"]
    for page_data in sld_pages:
        page_rels = _extract_sld_relationships(page_data, equipment)
        for upstream_id, downstream_id in page_rels:
            if upstream_id in nodes and downstream_id in nodes:
                relationships.append((upstream_id, downstream_id, page_data["page"]))

    # Step 3: Extract relationships from panel schedules and equipment schedules
    schedule_pages = [p for p in pages if p.get("page_type") in ("panel_schedule", "equipment_schedule")]
    for page_data in schedule_pages:
        page_rels = _extract_schedule_relationships(page_data, equipment, nodes)
        for upstream_id, downstream_id in page_rels:
            if upstream_id in nodes and downstream_id in nodes:
                relationships.append((upstream_id, downstream_id, page_data["page"]))

    # Step 4: Infer bus → breaker hierarchy on same page
    page_rels = _infer_page_hierarchy(equipment)
    for upstream_id, downstream_id in page_rels:
        if upstream_id in nodes and downstream_id in nodes:
            # Don't duplicate existing relationships
            existing = {(r[0], r[1]) for r in relationships}
            if (upstream_id, downstream_id) not in existing:
                relationships.append((upstream_id, downstream_id, 0))

    # Apply relationships to nodes
    for upstream_id, downstream_id, page in relationships:
        up_node = nodes.get(upstream_id)
        down_node = nodes.get(downstream_id)
        if up_node and down_node:
            if downstream_id not in up_node.downstream_ids:
                up_node.downstream_ids.append(downstream_id)
            down_node.upstream_id = upstream_id

    # Identify root nodes (no upstream)
    root_nodes = [nid for nid, node in nodes.items() if node.upstream_id is None]

    # Step 5: Propagate fault current
    _propagate_fault_current(nodes, root_nodes, equipment)

    return SystemTopology(nodes=nodes, root_nodes=root_nodes, relationships=relationships)


# ---------------------------------------------------------------------------
#  Relationship Extraction
# ---------------------------------------------------------------------------

def _extract_sld_relationships(page_data: dict, equipment: list) -> list:
    """Extract upstream/downstream relationships from SLD page text."""
    relationships = []
    text = page_data["text"]
    text_lower = page_data["text_lower"]
    page_num = page_data["page"]

    # Get equipment on this page
    page_equipment = [eq for eq in equipment if eq.page_number == page_num]
    if not page_equipment:
        return relationships

    # Pattern: "INCOMING" near a breaker → this is an incoming feeder (upstream end)
    # Pattern: "OUTGOING" near a breaker → this feeds something downstream
    for eq in page_equipment:
        if eq.equipment_type != "breaker":
            continue

        # Look at the raw_text context for this equipment
        context = (eq.raw_text or "").lower()
        designation = eq.designation

        # "SOURCE A INCOMER", "SOURCE B INCOMER" → root/utility feed
        if "incomer" in context or "incoming" in context:
            # This is a main incoming breaker — mark as root-level
            # Look for what it feeds by checking other breakers on this page
            pass

        # "OUTGOING" → this breaker feeds something
        if "outgoing" in context:
            # Look for the load description: "IT UPS", "MECH UPS", "CHILLER", "NETWORK", etc.
            load_match = re.search(
                r'(?:outgoing|feed(?:ing|s)?)\s*(?:to\s+)?([\w\s\-]+?)(?:\n|$)',
                context
            )
            if load_match:
                load_desc = load_match.group(1).strip().upper()
                # Try to match to another equipment item
                for other_eq in page_equipment:
                    if other_eq.designation == designation:
                        continue
                    if other_eq.equipment_type == "breaker" and "incoming" in (other_eq.raw_text or "").lower():
                        # This outgoing feeds that incoming
                        relationships.append((designation, other_eq.designation))

    # Pattern: breakers listed under a bus section → bus feeds those breakers
    # Look for bus/busbar references followed by breaker lists
    bus_panels = [eq for eq in page_equipment if eq.equipment_type == "panel" and eq.amperage]
    breakers = [eq for eq in page_equipment if eq.equipment_type == "breaker"]

    for bus in bus_panels:
        bus_amps = _parse_amps(bus.amperage)
        if not bus_amps:
            continue
        # Breakers with smaller ratings on same page likely feed from this bus
        for bkr in breakers:
            bkr_amps = _parse_amps(bkr.trip_rating or bkr.frame_size)
            if bkr_amps and bkr_amps < bus_amps:
                relationships.append((bus.designation, bkr.designation))

    # ABB-specific: Q-designations establish hierarchy
    # Larger Q numbers are typically downstream of smaller ones in ABB SLDs
    q_breakers = []
    for eq in page_equipment:
        if eq.equipment_type != "breaker":
            continue
        q_match = re.search(r'Q(\d+)', eq.raw_text or "")
        if q_match:
            q_breakers.append((int(q_match.group(1)), eq))

    # Sort by Q number — lower Q = more upstream (Q1, Q2 = mains)
    q_breakers.sort(key=lambda x: x[0])

    return relationships


def _extract_schedule_relationships(page_data: dict, equipment: list, nodes: dict) -> list:
    """Extract relationships from panel schedule / equipment schedule pages."""
    relationships = []
    text_lower = page_data["text_lower"]

    # Look for "FED FROM" patterns
    fed_from_patterns = [
        r'fed\s+from\s*[:=]?\s*([\w\-]+)',
        r'source\s*[:=]?\s*([\w\-]+)',
        r'incoming\s+from\s*[:=]?\s*([\w\-]+)',
        r'main\s+(?:breaker|fuse)\s*[:=]?\s*(\d+)\s*a',
    ]

    for pattern in fed_from_patterns:
        for match in re.finditer(pattern, text_lower):
            source = match.group(1).strip().upper()
            # Find which equipment on this page could be the downstream
            page_equipment = [eq for eq in equipment if eq.page_number == page_data["page"]]
            for eq in page_equipment:
                if eq.equipment_type in ("panel", "breaker"):
                    # Try to match source to a known node
                    if source in nodes:
                        relationships.append((source, eq.designation))

    return relationships


def _infer_page_hierarchy(equipment: list) -> list:
    """Infer bus → breaker relationships from equipment on the same page."""
    relationships = []

    # Group by page
    by_page = {}
    for eq in equipment:
        by_page.setdefault(eq.page_number, [])
        by_page[eq.page_number].append(eq)

    for page_num, page_equip in by_page.items():
        panels = [eq for eq in page_equip if eq.equipment_type == "panel" and eq.amperage]
        breakers = [eq for eq in page_equip if eq.equipment_type == "breaker"]

        if not panels or not breakers:
            continue

        # The largest-rated panel on a page likely feeds the breakers
        panels_sorted = sorted(panels, key=lambda p: _parse_amps(p.amperage) or 0, reverse=True)
        main_panel = panels_sorted[0]
        main_amps = _parse_amps(main_panel.amperage) or 0

        for bkr in breakers:
            bkr_amps = _parse_amps(bkr.trip_rating or bkr.frame_size) or 0
            if 0 < bkr_amps < main_amps:
                relationships.append((main_panel.designation, bkr.designation))

    return relationships


# ---------------------------------------------------------------------------
#  Fault Current Propagation
# ---------------------------------------------------------------------------

def _propagate_fault_current(nodes: dict, root_nodes: list, equipment: list):
    """Propagate estimated available fault current down through the topology.

    Estimation approach (when actual fault study is not available):

    Source A (Utility): Assume infinite bus upstream of an unknown MV transformer.
    Typical 480V secondary fault currents for common MV transformer sizes:
      - 1000kVA, 5.75% Z: ~20kA
      - 1500kVA, 5.75% Z: ~30kA
      - 2000kVA, 5.75% Z: ~40kA
      - 2500kVA, 5.75% Z: ~50kA
    We use 42kA as a conservative-typical estimate for utility-fed 480V systems.

    Source B (Generator): Generator subtransient fault contribution is typically
    6-10x rated current (Xd" typically 12-17% for diesel gensets).
    For a data center with 2000kW generators at 480V:
      - Rated I = 2000kW / (480V × 1.732 × 0.8pf) ≈ 3000A
      - Subtransient: ~8x = ~24kA
    We estimate generator contribution at 20kA for a typical DC generator.

    Combined: When both sources can feed the bus (through bus tie), AFC is
    the sum of both contributions: ~42 + 20 = ~62kA.

    These are ESTIMATES for flagging obviously undersized equipment.
    The actual fault current study is always required.
    """
    # Look for actual AFC values in the SLD text
    actual_afc = _search_for_stated_afc(nodes, equipment)

    if actual_afc:
        # Use the stated value
        service_afc_kA = actual_afc
    else:
        # Estimate based on system voltage and source type
        # Check if we have dual sources (utility + generator)
        has_generator_source = any(
            "generator" in (n.description or "").lower() or
            "gen" in (n.description or "").lower() or
            "source b" in (n.description or "").lower()
            for n in nodes.values()
        )
        has_utility_source = any(
            "utility" in (n.description or "").lower() or
            "mains" in (n.description or "").lower() or
            "source a" in (n.description or "").lower() or
            "incomer" in (n.description or "").lower()
            for n in nodes.values()
        )

        utility_afc = 42.0   # kA — typical 2000kVA MV transformer, 5.75% Z, infinite bus primary
        generator_afc = 20.0  # kA — typical 2000kW diesel genset, ~12% Xd"

        if has_utility_source and has_generator_source:
            # Both sources can contribute through bus tie
            service_afc_kA = utility_afc + generator_afc  # ~62kA
        elif has_generator_source:
            service_afc_kA = generator_afc
        else:
            service_afc_kA = utility_afc

    for root_id in root_nodes:
        root = nodes.get(root_id)
        if root:
            root.available_fault_current_kA = service_afc_kA
            _propagate_down(nodes, root_id, service_afc_kA, equipment)


def _search_for_stated_afc(nodes: dict, equipment: list) -> Optional[float]:
    """Look for explicitly stated available fault current values in equipment descriptions."""
    for eq in equipment:
        raw = (eq.raw_text or "").lower()
        # Look for "available fault current: 65kA" or "AFC: 65kA" or "short circuit: 65kA"
        patterns = [
            r'available\s+fault\s+current\s*[:=]\s*(\d+)\s*ka',
            r'afc\s*[:=]\s*(\d+)\s*ka',
            r'short\s*circuit\s*(?:current)?\s*[:=]\s*(\d+)\s*ka',
        ]
        for pattern in patterns:
            m = re.search(pattern, raw)
            if m:
                return float(m.group(1))
    return None


def _propagate_down(nodes: dict, node_id: str, afc_kA: float, equipment: list):
    """Recursively propagate AFC down the tree."""
    node = nodes.get(node_id)
    if not node:
        return

    node.available_fault_current_kA = afc_kA

    for child_id in node.downstream_ids:
        child = nodes.get(child_id)
        if not child:
            continue

        child_afc = afc_kA  # Default: same as parent

        # If child is a transformer, recalculate AFC on secondary
        child_equip = _find_equipment(equipment, child_id)
        if child_equip and child_equip.equipment_type == "transformer":
            kva = float(child_equip.kva) if child_equip.kva else 0
            imp = float(child_equip.impedance) if child_equip.impedance else 0
            sec_v = _parse_voltage(child_equip.secondary_voltage or child_equip.voltage) or 480

            if kva > 0 and imp > 0:
                child_afc = transformer_secondary_fault_current(kva, sec_v, imp) / 1000  # Convert to kA

        _propagate_down(nodes, child_id, child_afc, equipment)


def _find_equipment(equipment: list, designation: str) -> Optional[ExtractedEquipment]:
    """Find equipment by designation."""
    for eq in equipment:
        if eq.designation == designation:
            return eq
    return None


# ---------------------------------------------------------------------------
#  Helpers
# ---------------------------------------------------------------------------

def _parse_amps(val: Optional[str]) -> Optional[int]:
    if not val:
        return None
    m = re.search(r'(\d+)', str(val))
    return int(m.group(1)) if m else None


def _parse_kA(val: Optional[str]) -> Optional[int]:
    if not val:
        return None
    m = re.search(r'(\d+)', str(val))
    return int(m.group(1)) if m else None


def _parse_voltage(val: Optional[str]) -> Optional[int]:
    if not val:
        return None
    m = re.search(r'(\d{3,5})', str(val))
    return int(m.group(1)) if m else None
