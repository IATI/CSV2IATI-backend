import os
import urllib2
from datetime import date
from datetime import datetime
import json
import csv
import pprint
from xml.etree.cElementTree import Element, ElementTree

def create_IATI_xml(iatidata, dir, o):
    node = Element('iati-activities')
    node.set("version", "1.0")
    current_datetime = datetime.now().replace(microsecond=0).isoformat()
    node.set("generated-datetime",current_datetime)
    for activity in iatidata:
        a = Element("iati-activity")
        a.set("xml:lang", o["lang"])
        a.set("default-currency", o["default-currency"])
        node.append(a)
        
        ro = Element("reporting-org")
        ro.set("ref", o["reporting-org"]["ref"])
        ro.set("type", o["reporting-org"]["type"])
        ro.text = o["reporting-org"]["text"]
        a.append(ro)
        for field in activity:
            for key, val in field.items():
                if key == "transaction":
                    transactions = Element("transaction")
                    a.append(transactions)
                    for trans_data, trans_data_value in val.items():
                        transaction_field = Element(trans_data)
                        for attrib, attrib_value in trans_data_value.items():
                            if (attrib == 'text'):
                                try:
                                    attrib_value.decode('ascii')
                                except UnicodeDecodeError:
                                    transaction_field.text = attrib_value
                                else:
                                    transaction_field.text = attrib_value
                            else:
                                try:
                                    str(attrib_value).decode('ascii')
                                except UnicodeDecodeError:
                                    transaction_field.set(attrib, unicode(str(attrib_value), "utf-8"))
                                else:
                                    transaction_field.set(attrib, str(attrib_value))
                        transactions.append(transaction_field)
                else:
                    key = Element(key)
                    for attrib, attrib_value in val.items():
                        if (attrib == 'text'):
                            try:
                                attrib_value.decode('ascii')
                            except UnicodeDecodeError:
                                key.text = unicode(attrib_value, "utf-8")
                            else:
                                key.text = attrib_value
                        else:
                            try:
                                str(attrib_value).decode('ascii')
                            except UnicodeDecodeError:
                                key.set(attrib, unicode(str(attrib_value), "utf-8"))
                            else:
                                key.set(attrib, str(attrib_value))
                    a.append(key)
    doc = ElementTree(node)
    XMLfilename = dir + '/IATI.xml'
    doc.write(XMLfilename)

    print "IATI-XML file saved to ", XMLfilename

def parse_csv(dir):
    csvfile = open(dir + '/csv.csv', 'r')
    csvdata=csv.DictReader(csvfile)
    jsonfile = open(dir + '/json.json', 'r')
    jsondata = json.loads(jsonfile.read())
    
    # Look in organisation section of JSON file for default organisation fields.
    o = jsondata["organisation"]
    
    # Look in mapping section of JSON file for IATI fields, construct a dict from that.
    m = jsondata["mapping"]
    
    iatidata = []
    for line in csvdata:
        linedata = []
        try:
            for field in m:
                fielddata= {}
                iati_field = m[field]["iati_field"]
                fielddata[iati_field] = {}
                # if it's a compound field, then get the different elements ...
                # NB if a field has no text, then it must be a compound field, even if it only has one attribute ...
                if (m[field]["type"] == "compound"):
                    for part in m[field]["fields"]:
                        if (m[field]["fields"][part]["type"] == 'constant'):
                            fielddata[iati_field][part] = m[field]["fields"][part]["constant"]
                        else:
                            part_column = m[field]["fields"][part]["column"]
                            if ((m[field]["fields"][part].has_key("datatype")) and (m[field]["fields"][part]["datatype"] == 'float')):
                                try:
                                    fielddata[iati_field][part] = float(line[part_column])
                                except:
                                    fielddata[iati_field][part] = '0'
                            else:
                                fielddata[iati_field][part] = line[part_column]                                
                            del part_column
                # it's transaction data, so break it down
                elif (m[field]["type"] == "transaction"):
                    iati_field = m[field]["iati_field"]
                    fielddata[iati_field] = {}
                    # got e.g. transaction type
                    for transactionfield in m[field]["transaction_data_fields"]:
                        transaction_iati_field = m[field]["transaction_data_fields"][transactionfield]["iati_field"]
                        fielddata[iati_field][transaction_iati_field] = {}
                        # got e.g. transaction type code
                        for part in m[field]["transaction_data_fields"][transactionfield]["fields"]:
                            if (m[field]["transaction_data_fields"][transactionfield]["fields"][part]["type"] == 'constant'):
                                fielddata[iati_field][transaction_iati_field][part] = m[field]["transaction_data_fields"][transactionfield]["fields"][part]["constant"]
                            else:
                                part_column = m[field]["transaction_data_fields"][transactionfield]["fields"][part]["column"]
                                if (m[field]["transaction_data_fields"][transactionfield]["fields"][part]).has_key("stripchars"):
                                    fielddata[iati_field][transaction_iati_field][part] = (line[part_column].strip().replace(m[field]["transaction_data_fields"][transactionfield]["fields"][part]["stripchars"], ""))
                                else:
                                    fielddata[iati_field][transaction_iati_field][part] = line[part_column]
                                del part_column
                            
                else:
                    # otherwise, it's just a text field ...
                    if (m[field].has_key("prefix")):
                        prefix = m[field]["prefix"]
                    else:
                        prefix = ""
                    if (m[field]["type"] == "column"):
                        field_column = m[field]["column"]
                    else:
                        field_constant = m[field]["constant"]
                    try:
                        fielddata[iati_field]["text"] = prefix + line[field_column]
                    except NameError:
                        fielddata[iati_field]["text"] = field_constant
                try:
                    del field_column 
                    del field_constant
                    del fielddata[iati_field]
                except:
                    pass
                linedata.append(fielddata)
            iatidata.append(linedata)
        except KeyError, e:
            raise Exception("Unknown column: ", e)
    create_IATI_xml(iatidata, dir, o)
 
def save_file(url, thetype, dir):
    req = urllib2.Request(url)
    try:
        if (thetype == 'csv'):
	        filename = 'csv.csv'
        elif (thetype == 'json'):
	        filename = 'json.json'
        webFile = urllib2.urlopen(req)
        localFile = open(dir + '/' + filename, 'w')
        localFile.write(webFile.read())
        localFile.close()
        webFile.close()
    except urllib2.HTTPError, e:
        print "ERROR: The server couldn't fulfill the request."
        print "Error code: ", e.code
        raise Exception
    except urllib2.URLError, e:
        print "ERROR: Could not reach the server."
        print "Reason: ", e.reason
        raise Exception

def get_files():
    if (len(sys.argv) > 2):
        csvfile = sys.argv[1]
        modelfile = sys.argv[2]
        #dir = 'temp/' + str(datetime.now())
        dir = 'temp/' + str(date.today())
        if not os.path.exists(dir):
            try:
                os.makedirs(dir)
            except Exception, e:
                print "Failed:", e
                print "Couldn't create directory"
        try:
            print "Saving CSV file..."
            save_file(csvfile, 'csv', dir)
            print "Saving mapping file..."
            save_file(modelfile, 'json', dir)
        except Exception, e:
            print "Couldn't save files."
            print ""
            print "Filenames need to be provided as full URLs. For example, on your local machine, you might type something like:"
            print """python run.py file:///home/YOUR_USER_NAME/PATH_TO_CSV_IATI_CONVERTER/testdata/oxfamiati.csv file:///home/YOUR_USER_NAME/PATH_TO_CSV_IATI_CONVERTER/testdata/json.json"""
            print ""
            print "You provided the following files:"
            print csvfile
            print modelfile
        else:
            print "Saved files"
            parse_csv(dir)
    else:
        print "Required arguments: csvfile model"
    
if __name__ == '__main__':
    import sys
    print ""
    print "CSV to IATI converter"
    print "====================="
    print ""
    try:
        get_files()
    except Exception, e:
        print 'Failed:', e
