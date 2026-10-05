"""HL7 v2 → XML conversion (well-formed generic serialization)."""
from __future__ import annotations

from xml.etree import ElementTree as ET
from xml.dom import minidom


def to_xml(parsed: dict) -> str:
    """Return a well-formed XML document.

    Structure:
      <HL7Message schema="hl7v2-xml-generic" version="1.0">
        <Delimiters field="|" component="^" .../>
        <Overview>...</Overview>
        <Segments>
          <Segment name="PID" index="1">
            <Field position="3" raw="...">
              <Repetition index="0">
                <Component index="0">
                  <Subcomponent index="0">value</Subcomponent>
                </Component>
              </Repetition>
            </Field>
          </Segment>
        </Segments>
      </HL7Message>
    """
    root = ET.Element("HL7Message", {
        "schema": "hl7v2-xml-generic",
        "version": "1.0",
        "note": "Generic HL7 v2 XML serialization; not HL7 v2.xml encoding.",
    })

    delims = ET.SubElement(root, "Delimiters")
    for k, v in parsed["delimiters"].items():
        ET.SubElement(delims, "Delimiter", {"name": k, "value": v})

    ov = ET.SubElement(root, "Overview")
    for k, v in parsed["overview"].items():
        child = ET.SubElement(ov, "Item", {"name": k})
        child.text = "" if v is None else str(v)

    segs_el = ET.SubElement(root, "Segments")
    for seg in parsed["segments"]:
        seg_el = ET.SubElement(segs_el, "Segment", {
            "name": seg["name"], "index": str(seg["index"]),
        })
        for f in seg["fields"]:
            field_el = ET.SubElement(seg_el, "Field", {
                "position": str(f["position"]),
                "raw": f["raw"],
            })
            for ri, rep in enumerate(f["repetitions"]):
                rep_el = ET.SubElement(field_el, "Repetition", {"index": str(ri)})
                for ci, comp in enumerate(rep["components"]):
                    comp_el = ET.SubElement(rep_el, "Component", {"index": str(ci)})
                    for si, sub in enumerate(comp["subcomponents"]):
                        sub_el = ET.SubElement(comp_el, "Subcomponent", {"index": str(si)})
                        sub_el.text = sub["value"]

    rough = ET.tostring(root, encoding="utf-8")
    pretty = minidom.parseString(rough).toprettyxml(indent="  ", encoding="utf-8")
    return pretty.decode("utf-8")