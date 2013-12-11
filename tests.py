import unittest
import csviati
import os
import json
import copy
import xml.etree.cElementTree as etree

basic_organisation = {
                        'data-encoding': 'ascii',
                        'lang': 'en',
                        'default-currency': 'GBP',
                        'reporting-org':{
                            'text': 'Test',
                            'ref': 'test',
                            'type': '10',
                        },
                        'contact-info': {
                            'person-name': 'Test Test',
                            'telephone': '0test',
                            'email': 'test@example.com',
                            'address': 'Test Street'
                        }
                    }

def conversion_wrapper(csv_contents, json_dict):
    with csviati.app.test_request_context():
        dir_name = 'testtmp'
        try:
            os.makedirs(os.path.join(csviati.UPLOAD_FILES_BASE, dir_name))
        except OSError, e:
            if e.errno != 17: raise e
        with open(os.path.join(csviati.UPLOAD_FILES_BASE, dir_name, 'csv.csv'), 'w') as fp:
            fp.write(csv_contents)
        with open(os.path.join(csviati.UPLOAD_FILES_BASE, dir_name, 'json.json'), 'w') as fp:
            json.dump(json_dict, fp)
        fname = csviati.parse_csv(dir_name).split('/')[-1]
        tree = etree.parse(os.path.join(csviati.UPLOAD_FILES_BASE, dir_name, fname))
        return tree

def text_column(column_name, iati_field=None):
    out = {
        'datatype': 'compound',
        'fields': {
            'text': {
                'datatype': 'column',
                'column': column_name
            }
        }
    }
    if iati_field:
        out['iati-field'] = iati_field
    return out

class TestSequenceFunctions(unittest.TestCase):
    def setUp(self):
        pass

    def test_save_file_file_fails(self):
        self.assertRaises(csviati.Error, csviati.save_file, 'file:///etc/passwd', 'csv', '.')

    def test_conversion_basic(self):
            organisation = copy.deepcopy(basic_organisation)
            organisation['contact-info']['add-to-activities'] = [ 'true' ]
            tree = conversion_wrapper("""a,b
42,3
43,4
""",
                {
                    'organisation': organisation,
                    'mapping': {
                        'test1': text_column('a', 'test-el'),
                        'test2': {
                            'datatype': 'compound',
                            'iati-field': 'another-test-el',
                            'fields': {
                                'test-att': {
                                    'datatype': 'column',
                                    'column': 'b'
                                }
                            }
                        }
                    }
                })
            root = tree.getroot()
            self.assertEquals(root.tag, 'iati-activities')
            self.assertEquals(len(root), 2)
            for child in root:
                self.assertEquals(child.tag, 'iati-activity')

                self.assertEquals(len(child.findall('reporting-org')), 1)
                reporting_org = child.find('reporting-org')
                self.assertEquals(reporting_org.text, 'Test')
                self.assertEquals(reporting_org.attrib['ref'], 'test')
                self.assertEquals(reporting_org.attrib['type'], '10')

                self.assertEquals(len(child.findall('contact-info')), 1)
                contact_info = child.find('contact-info')
                self.assertEquals(contact_info.find('person-name').text, 'Test Test')
                self.assertEquals(contact_info.find('telephone').text, '0test')
                self.assertEquals(contact_info.find('email').text, 'test@example.com')
                self.assertEquals(contact_info.find('mailing-address').text, 'Test Street')

                self.assertEquals(len(child.findall('test-el')), 1)
                self.assertEquals(len(child.findall('another-test-el')), 1)
                self.assertEquals(child.find('another-test-el').text, None)
            self.assertEquals(root[0].find('test-el').text, '42')
            self.assertEquals(root[1].find('test-el').text, '43')
            self.assertEquals(root[0].find('another-test-el').attrib['test-att'], '3')
            self.assertEquals(root[1].find('another-test-el').attrib['test-att'], '4')


    def test_conversion_contact(self):
            tree = conversion_wrapper("""person_name,b
Alice,3
""",
                {
                    'organisation': basic_organisation,
                    'mapping': {
                        'contact-info': {
                            'datatype': 'compound',
                            'iati-field': 'contact-info',
                            'fields': {
                                'person-name': text_column('person_name')
                            }
                        }
                    }
                })
            root = tree.getroot()
            contact_infos = root[0].findall('contact-info')
            self.assertEquals(len(contact_infos), 1)
            self.assertIn('Alice', [ c.find('person-name').text for c in contact_infos ])

    def test_hierarchy(self):
            tree = conversion_wrapper("""hierarchy_column,b
2,3
""",
                {
                    'organisation': basic_organisation,
                    'mapping': {
                        'test1': {
                            'datatype': 'column',
                            'iati-field': 'hierarchy',
                            'column': 'hierarchy_column'
                        }
                    }
                })
            root = tree.getroot()
            self.assertEquals(root[0].findall('hierarchy'), [])
            self.assertEquals(root[0].attrib['hierarchy'], '2')


if __name__ == '__main__':
    unittest.main()
