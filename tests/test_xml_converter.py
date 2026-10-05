from xml.etree import ElementTree as ET
from app.services.parser import parse_message
from app.services.xml_converter import to_xml

def test_xml_is_wellformed():
    msg = "MSH|^~\\&|A|B|C|D|20240101||ADT^A01|1|P|2.5\rPID|1||123^^^MRN||DOE^JOHN\r"
    xml = to_xml(parse_message(msg))
    root = ET.fromstring(xml)
    assert root.tag == "HL7Message"

def test_xml_escapes_special_chars():
    msg = 'MSH|^~\\&|A|B|C|D|20240101||ADT^A01|1|P|2.5\rNTE|1||A & B <tag>\r'
    xml = to_xml(parse_message(msg))
    # Should parse without error and contain escaped entities in source
    ET.fromstring(xml)
    assert "&amp;" in xml
    assert "&lt;" in xml