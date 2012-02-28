import sys
import os
import urllib2
import time
from datetime import date, datetime
import json
import csv
import pprint
import codecs
import unicode_dict_reader as udr
from xml.etree.cElementTree import Element, ElementTree
from flask import Flask, render_template, flash, request, Markup
app = Flask(__name__)

# Process the data created in parse_csv()
def create_IATI_xml(iatidata, dir, o):
    #iatidata contains the activities
    #o contains the organisation data
    output = ''
    node = Element('iati-activities')
    node.set("version", "1.0")
    current_datetime = datetime.now().replace(microsecond=0).isoformat()
    node.set("generated-datetime",current_datetime)
    for activity in iatidata:
        #for each activity, create one <iati-activity>
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
        #e.g. activity['activity-date']
            for key, val in field.items():
            #e.g. activity['activity-date']['fields']
                if key == "transaction":
                    transactions = Element("transaction")
                    a.append(transactions)
                    for trans_data, trans_data_value in val.items():
                        transaction_field = Element(trans_data)
                        for attrib, attrib_value in trans_data_value.items():
                            if (attrib == 'text'):
                                transaction_field.text = attrib_value
                            else:
                                transaction_field.set(attrib, str(attrib_value))
                        transactions.append(transaction_field)
                else:
                    key = Element(key)
                    for attrib, attrib_value in val.items():
                        if (attrib == 'text'):
                            key.text = attrib_value
                        else:
                            key.set(attrib, str(attrib_value))
                    a.append(key)
    doc = ElementTree(node)        
    XMLfilename = dir + '/' + str(time.time()) + '.xml'
    doc.write(XMLfilename)
    XMLfilename_html = request.url_root + XMLfilename
    output += "<p>IATI-XML file saved to <a href=\"" + XMLfilename_html + "\">" + XMLfilename_html + "</a></p>"
    return output

# Process the mapping file and parse the CSV according to those rules, to construct a big list in "iatidata"
def parse_csv(dir):
    output = ''
    csvfile = open(dir + '/csv.csv', 'r')
    csvdata=udr.UnicodeDictReader(csvfile)
    jsonfile = open(dir + '/json.json', 'r')
    jsondata = json.loads(jsonfile.read())
    
    # Look in organisation section of JSON file for default organisation fields.
    o = jsondata["organisation"]
    
    # Look in mapping section of JSON file for IATI fields, construct a dict from that.
    m = jsondata["mapping"]
    
    #iatidata will contain all of the data from the CSV file plus the mapping
    iatidata = []
    for line in csvdata:
        #linedata will contain one line of data (one activity, if the data structure is one line per activity)
        linedata = []
        try:
            for field in m:
                #field = the dimension in the JSON mapping file. This can be anything as long as it's unique within the JSON.
                fielddata= {}
                #fielddata = the hash to contain all of this dimension's data
                iati_field = m[field]["iati-field"]
                #iati_field contains the name of the IATI field this dimension should output.
                fielddata[iati_field] = {}
                
                # NB all input has to be either as a compound field or as a transaction field, with multiple items in 'field'
                # if the dimension (field) is of datatype compound:
                if (m[field]["datatype"] == "compound"):
                    for part in m[field]["fields"]:
                        # in the dimension mapping, the variable 'part' is called 'field'. Should probably make this more consistent...
                        if (m[field]["fields"][part]["datatype"] == 'constant'):
                            fielddata[iati_field][part] = m[field]["fields"][part]["constant"]
                        else:
                            part_column = m[field]["fields"][part]["column"]
                            if ((m[field]["fields"][part].has_key("datatype")) and (m[field]["fields"][part]["datatype"] == 'float')):
                                try:
                                    fielddata[iati_field][part] = float(line[part_column])
                                    if (str(float(line[part_column])) == '-0.0'):
                                        fielddata[iati_field][part] = '0'
                                except:
                                    fielddata[iati_field][part] = '0'
                            else:
                                if (m[field]["fields"][part].has_key("text-transform-type")):
                                    if (m[field]["fields"][part]["text-transform-type"] == "date"):
                                        text_transform_format = m[field]["fields"][part]["text-transform-format"]
                                        thedata = line[part_column].strip()
                                        try:
                                            newdate = datetime.strptime(thedata, text_transform_format).strftime("%Y-%m-%d")
                                            fielddata[iati_field][part] = str(newdate)
                                            
                                        except ValueError, e:
                                            output += "Failed to convert date:", e
                                            pass
                                else:
                                    fielddata[iati_field][part] = line[part_column].strip()
                            del part_column
                # it's transaction data, so break it down
                elif (m[field]["datatype"] == "transaction"):
                    iati_field = m[field]["iati-field"]
                    fielddata[iati_field] = {}
                    # got each transaction field...
                    for transactionfield in m[field]["tdatafields"]:
                        transaction_iati_field = m[field]["tdatafields"][transactionfield]["iati-field"]
                        fielddata[iati_field][transaction_iati_field] = {}
                        # 
                        for part in m[field]["tdatafields"][transactionfield]["fields"]:
                            if (m[field]["tdatafields"][transactionfield]["fields"][part]["datatype"] == 'constant'):
                                fielddata[iati_field][transaction_iati_field][part] = m[field]["tdatafields"][transactionfield]["fields"][part]["constant"]
                            else:
                                part_column = m[field]["tdatafields"][transactionfield]["fields"][part]["column"]
                                if (m[field]["tdatafields"][transactionfield]["fields"][part]).has_key("stripchars"):
                                    fielddata[iati_field][transaction_iati_field][part] = (line[part_column].strip().replace(m[field]["tdatafields"][transactionfield]["fields"][part]["stripchars"], ""))
                                else:
                                    fielddata[iati_field][transaction_iati_field][part] = line[part_column]
                                del part_column
                try:
                    del field_column 
                    del field_constant
                    #del fielddata[iati_field]
                except:
                    pass
                linedata.append(fielddata)
            iatidata.append(linedata)
        except KeyError, e:
            raise Exception("Unknown column: ", e)
    flash("Parsed files", 'good')
    output += create_IATI_xml(iatidata, dir, o)
    return output
 
# Save the fiels received
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
        output += "ERROR: The server couldn't fulfill the request."
        output += "Error code: ", e.code
        return output
        raise Exception
    except urllib2.URLError, e:
        output += "ERROR: Could not reach the server."
        output += "Reason: ", e.reason
        return output
        raise Exception

# Receive the files as inputs from the command line
def get_files():
    if (request.form['csv_url'] != '') and (request.form['model_url'] != ''):
        csvfile = request.form['csv_url']
        modelfile = request.form['model_url']
        dir = 'static/' + str(date.today())
        output = ''
        import os
        os.getcwd()
        if not os.path.exists(dir):
            try:
                os.makedirs(dir)
            except Exception, e:
                flash(("Failed:", e),'bad')
                flash("Couldn't create directory", 'bad')
        try:
            flash("Saving CSV file...", 'notice')
            save_file(csvfile, 'csv', dir)
            flash("Saving mapping file...", 'notice')
            save_file(modelfile, 'json', dir)
        except Exception, e:
            flash("Couldn't save files.", 'bad')
            output += "<p>Files need to be provided as full URLs.</p>"
            output += "<p>You provided the following URLs:"
            output += "<p>CSV file: " + csvfile + "</p>"
            output += "<p>Model file: " + modelfile + "</p>"
            return output
        else:
            flash("Saved files", 'good')
            output += parse_csv(dir)
            return output
    else:
        return "Required arguments: csv_url model_url"

@app.route("/", methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        return doConversion()
    else:
        return showPostForm()

def doConversion():
    return render_template('output.html', output=Markup(get_files()))

def showPostForm():
    return render_template('form.html')

app.secret_key = ')MrYYKq#!xXxrbkWmHJPRQiZhRL@1Te_:cgg`wyp83ac4KZ}A3tuJ*9{o)(*+4)'

if __name__ == '__main__':
    if (len(sys.argv) > 1):
        port = int(sys.argv[1])
        app.run(debug=True,port=port)
    else:
        app.run(debug=True,port=5001)
