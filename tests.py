import unittest
import csviati
import os
import json
import xml.etree.cElementTree as etree

class TestSequenceFunctions(unittest.TestCase):
    def setUp(self):
        pass

    def test_save_file_file_fails(self):
        self.assertRaises(csviati.Error, csviati.save_file, 'file:///etc/passwd', 'csv', '.')

    def test_basic_conversion(self):
        with csviati.app.test_request_context():
            dir_name = os.path.join('testtmp', 'basic_conversion')
            try:
                os.makedirs(os.path.join(csviati.UPLOAD_FILES_BASE, dir_name))
            except OSError, e:
                if e.errno != 17: raise e
            with open(os.path.join(csviati.UPLOAD_FILES_BASE, dir_name, 'csv.csv'), 'w') as fp:
                fp.write("""a,b
42,3
43,4
""")
            with open(os.path.join(csviati.UPLOAD_FILES_BASE, dir_name, 'json.json'), 'w') as fp:
                json.dump({
                    'organisation': {
                        'data-encoding': 'ascii',
                        'lang': 'en',
                        'default-currency': 'GBP',
                        'reporting-org':{
                            'text': 'Test',
                            'ref': 'test',
                            'type': '10',
                        }
                    },
                    'mapping': {
                        'test1': {
                            'datatype': 'compound',
                            'iati-field': 'test-el',
                            'fields': {
                                'text': {
                                    'datatype': 'column',
                                    'column': 'a'
                                }
                            }
                        },
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
                }, fp)
            fname = csviati.parse_csv(dir_name).split('/')[-1]
            tree = etree.parse(os.path.join(csviati.UPLOAD_FILES_BASE, 'testtmp', 'basic_conversion', fname))
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

                self.assertEquals(len(child.findall('test-el')), 1)
                self.assertEquals(len(child.findall('another-test-el')), 1)
                self.assertEquals(child.find('another-test-el').text, None)
            self.assertEquals(root[0].find('test-el').text, '42')
            self.assertEquals(root[1].find('test-el').text, '43')
            self.assertEquals(root[0].find('another-test-el').attrib['test-att'], '3')
            self.assertEquals(root[1].find('another-test-el').attrib['test-att'], '4')

if __name__ == '__main__':
    unittest.main()
