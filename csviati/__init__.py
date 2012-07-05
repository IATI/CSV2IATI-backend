import sys
import os
import urllib2
import time
from datetime import date, datetime
import json
import csv
import pprint
import codecs
import re
from xml.etree.cElementTree import Element, ElementTree
from flask import Flask, render_template, flash, request, Markup
app = Flask(__name__)
UPLOAD_FILES_BASE = '/usr/sites/CSV-IATI-Converter/'

def makeUnicode(data,encoding):
    try:
        nicedata = unicode(data, encoding=encoding, errors='ignore')
    except TypeError:
        nicedata = data
    # from http://boodebr.org/main/python/all-about-python-and-unicode#UNI_XML
    RE_XML_ILLEGAL = u'([\u0000-\u0008\u000b-\u000c\u000e-\u001f\ufffe-\uffff])' + \
                     u'|' + \
                     u'([%s-%s][^%s-%s])|([^%s-%s][%s-%s])|([%s-%s]$)|(^[%s-%s])' % \
                      (unichr(0xd800),unichr(0xdbff),unichr(0xdc00),unichr(0xdfff),
                       unichr(0xd800),unichr(0xdbff),unichr(0xdc00),unichr(0xdfff),
                       unichr(0xd800),unichr(0xdbff),unichr(0xdc00),unichr(0xdfff))
    x = nicedata
    x = re.sub(RE_XML_ILLEGAL, "?", nicedata)
    return x

def makePreviousEncoding(data,encoding):
    try:
        nicedata = data.encode(encoding, 'ignore')
    except TypeError:
        nicedata = data
    return nicedata

def newline_fix(column):
    newline_data = re.sub("\[newline\]", "\n", column)
    return newline_data

# Process the data created in parse_csv()
def create_IATI_xml(iatidata, dir, o):
    #iatidata contains the activities
    #o contains the organisation data
    output = ''
    node = Element('iati-activities')
    node.set("version", "1.0")
    current_datetime = datetime.now().replace(microsecond=0).isoformat()
    node.set("generated-datetime",current_datetime)
    character_encoding = o["data-encoding"]
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
    XMLfile = str(time.time()) + '.xml'
    XMLfilename = dir + '/' + XMLfile
    XMLabsfilename = UPLOAD_FILES_BASE + dir + '/' + XMLfile
    doc.write(XMLabsfilename)
    XMLfilename_html = request.url_root + XMLfilename
    output += "<p>IATI-XML file saved to <a href=\"" + XMLfilename_html + "\">" + XMLfilename_html + "</a></p>"
    return output

# Process the mapping file and parse the CSV according to those rules, to construct a big list in "iatidata"
def parse_csv(dir):
    #open in universal mode (fix Mac CSV encoding bug)
    #these temporary files should probably be made more unique...
    csvfile = open(UPLOAD_FILES_BASE + dir + '/csv.csv', 'rU')
    csvdata=csv.DictReader(csvfile)
    jsonfile = open(UPLOAD_FILES_BASE + dir + '/json.json', 'r')
    jsondata = json.loads(jsonfile.read())
    
    # Look in organisation section of JSON file for default organisation fields.
    o = jsondata["organisation"]
    
    # Look in mapping section of JSON file for IATI fields, construct a dict from that.
    m = jsondata["mapping"]
    
    # Look in organisation section of JSON file for character encoding
    character_encoding = jsondata["organisation"]["data-encoding"]
    
    # Handle multiple data structure
    if (("multiple" in o["data-structure"]) and (o["data-structure"]["multiple"] != "")):
        # if mapping has stated that there are multiple rows per sector (etc.), then collect all the iati-identifiers together
        iati_identifiers = set([])
        iati_identifiers_grouped_csvdata = {}
        for field in m:
            if (m[field]["iati-field"]=='iati-identifier'):
                column = m[field]["fields"]["text"]["column"]
                for line in csvdata:
                    iati_identifiers.add(line[column])
                    if (not(line[column] in iati_identifiers_grouped_csvdata)):
                        iati_identifiers_grouped_csvdata[line[column]] = []
                    iati_identifiers_grouped_csvdata[line[column]].append(line)
                    """ this creates, for each unique project ID, something like this (assuming project ID is 'PROJECT_1')
                     iati_identifiers_grouped_csvdata = {
                         'PROJECT_1' : [
                             "project ID" = "PROJECT_1",
                             "title" = "My project title",
                             "sector_name" = "First sector"
                         ],
                         'PROJECT_1' : [
                             "project ID" = "PROJECT_1",
                             "title" = "My project title",
                             "sector_name" = "Second sector"
                         ]
                        }
                    """
        

        multiple_fields = o["data-structure"]["multiple"]
        return get_csv_data(m, o, character_encoding, iati_identifiers_grouped_csvdata, dir, multiple_fields)
        """for line in iati_identifiers_grouped_csvdata[iati_identifier]:
            # write everything into the array. for the multiple field, just add a number to that field.
            return str(line)
        """
                
    # Handle single data structure
    else:
        return get_csv_data(m, o, character_encoding, csvdata, dir)
        
def get_csv_data(m, o, character_encoding, csvdata, dir, multiple_field=''):
    output = ''
    #iatidata will contain all of the data from the CSV file plus the mapping
    iatidata = []
    if (multiple_field):
        # for each unique iati identifier...
        for csvdata_group, csvdata_items in csvdata.items():
            # for each group, create a line of data
            linedata = []
            already_got_project_data = False
            """
            # csvdata_group is the name of the identifier
            # csvdata_items is the name of all the items within that identifier (each row in the individual spreadsheet)
            
            # loop through the items.
            # take all of the properties from the first item. Add the properties for each row for the multiple_field field.
            """
                        
            for line in csvdata_items:
                # for each row in the bundle of activities...
                # this is equivalent to "for line in csvdata"
                #
                # send to get_field_data, and therefore add to fielddata, if:
                # a) it's the first row in this group, or
                # b) the iati field is equal to the multiple fields field
                try:
                    # for each dimension in the mapping file...
                    for field in m:
                        #field = the dimension in the JSON mapping file. This can be anything as long as it's unique within the JSON.
                        try:
                            iati_field = m[field]["iati-field"]
                        except KeyError:
                            type, value, tb = sys.exc_info()
                            return "%s" % value.message
                        #iati_field contains the name of the IATI field this dimension should output.
                        if ((not already_got_project_data) or (iati_field == multiple_field)):
                            fielddata = get_field_data(iati_field, field, m, line, character_encoding)
                            linedata.append(fielddata)
                except KeyError, e:
                    type, value, tb = sys.exc_info()
                    return "ERROR: No such field: %s" % value.message
                # End of this row within the activity group... got the first row
                already_got_project_data = True
            # Finished this activity group, so write the activity
            iatidata.append(linedata)
        """ 
        csvdata will look slightly differently, as it will be grouped by unique iati identifiers
        for line in csvdata will get you the group
            for csvdata_item in csvdata will get you an individual row from the spreadsheet
        """
    else:
        for line in csvdata:
            #linedata will contain one line of data (one activity)
            linedata = []
            try:
                # for each dimension in the mapping file...
                for field in m:
                    #field = the dimension in the JSON mapping file. This can be anything as long as it's unique within the JSON.
                    try:                   
                        iati_field = m[field]["iati-field"]
                    except KeyError:
                        type, value, tb = sys.exc_info()
                        return "%s" % value.message
                    #iati_field contains the name of the IATI field this dimension should output.

                    fielddata = get_field_data(iati_field, field, m, line, character_encoding)
                    
                    # only append this to the data if the field is not empty
                    if (fielddata):
                        linedata.append(fielddata)
                iatidata.append(linedata)
            except KeyError, e:
                type, value, tb = sys.exc_info()
                return "ERROR: No such field: %s" % value.message
    flash("Parsed files", 'good')
    output += create_IATI_xml(iatidata, dir, o)
    return output
 
def get_field_data(iati_field, field, m, line, character_encoding):
    fielddata= {}
    #fielddata = the hash to contain all of this dimension's data
    fielddata[iati_field] = {}
    fielddata_empty_flag = False
    
    # NB all input has to be either as a compound field or as a transaction field, with multiple items in 'field'
    # if the dimension (field) is of datatype compound:
    if (m[field]["datatype"] == "compound"):
        for part in m[field]["fields"]:
            # in the dimension mapping, the variable 'part' is called 'field'. Should probably make this more consistent...
            if (m[field]["fields"][part]["datatype"] == 'constant'):
                fielddata[iati_field][part] = m[field]["fields"][part]["constant"]
            else:
                part_column = m[field]["fields"][part]["column"]
                part_column = newline_fix(part_column)
                if ((m[field]["fields"][part].has_key("datatype")) and (m[field]["fields"][part]["datatype"] == 'float')):
                    try:
                        fielddata[iati_field][part] = float(line[makePreviousEncoding(part_column, character_encoding)])
                        if (str(float(line[makePreviousEncoding(part_column, character_encoding)])) == '-0.0'):
                            fielddata[iati_field][part] = '0'
                    except:
                        fielddata[iati_field][part] = '0'
                else:
                    if (m[field]["fields"][part].has_key("text-transform-type")):
                        if (m[field]["fields"][part]["text-transform-type"] == "date"):
                            text_transform_format = m[field]["fields"][part]["text-transform-format"]
                            thedata = makeUnicode(line[makePreviousEncoding(part_column, character_encoding)], encoding=character_encoding).strip()
                            try:
                                newdate = datetime.strptime(thedata, text_transform_format).strftime("%Y-%m-%d")
                                fielddata[iati_field][part] = str(newdate)
                                
                            except ValueError, e:
                                output += "Failed to convert date:", e
                                pass
                    else:
                        # this is the bit that almost always does the work
                        fielddata[iati_field][part] = makeUnicode(line[makePreviousEncoding(part_column, character_encoding)], encoding=character_encoding).strip()
                if (fielddata[iati_field][part] == ''):
                    fielddata_empty_flag = True
                del part_column
    # it's transaction data, so break it down
    elif (m[field]["datatype"] == "transaction"):
        iati_field = m[field]["iati-field"]
        fielddata[iati_field] = {}
        # got each transaction field...
        for transactionfield in m[field]["tdatafields"]:
            transaction_iati_field = m[field]["tdatafields"][transactionfield]["iati-field"]
            fielddata[iati_field][transaction_iati_field] = {}
            
            for part in m[field]["tdatafields"][transactionfield]["fields"]:
                if (m[field]["tdatafields"][transactionfield]["fields"][part]["datatype"] == 'constant'):
                    fielddata[iati_field][transaction_iati_field][part] = m[field]["tdatafields"][transactionfield]["fields"][part]["constant"]
                else:
                    part_column = m[field]["tdatafields"][transactionfield]["fields"][part]["column"]
                    # replace [newline] on part_column with \n -- this is as a consequence of a fix in the modeleditor
                    part_column = newline_fix(part_column)
                    if (m[field]["tdatafields"][transactionfield]["fields"][part]).has_key("stripchars"):
                        fielddata[iati_field][transaction_iati_field][part] = (makeUnicode(line[makePreviousEncoding(part_column,encoding=character_encoding)].strip().replace(m[field]["tdatafields"][transactionfield]["fields"][part]["stripchars"], ""),encoding=character_encoding))
                    else:
                        fielddata[iati_field][transaction_iati_field][part] = (makeUnicode(line[makePreviousEncoding(part_column,encoding=character_encoding)],encoding=character_encoding))
                    # if the value field is empty, then discard this transaction
                    if ((fielddata[iati_field][transaction_iati_field][part] == '') and (transaction_iati_field == 'value') and (part == 'text')):
                        fielddata_empty_flag = True
                    del part_column
    try:
        del field_column 
        del field_constant
        #del fielddata[iati_field]
    except:
        pass

    if (fielddata_empty_flag):
        return False
    else:
        return fielddata
 
# Save the fields received
def save_file(url, thetype, dir):
    req = urllib2.Request(url)
    try:
        if (thetype == 'csv'):
	        filename = 'csv.csv'
        elif (thetype == 'json'):
	        filename = 'json.json'
        webFile = urllib2.urlopen(req)
        localFile = open(UPLOAD_FILES_BASE + dir + '/' + filename, 'w')
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
	#output = os.path.abspath(UPLOAD_FILES_BASE + dir)
        if not os.path.exists(UPLOAD_FILES_BASE + dir):
            try:
                os.makedirs(UPLOAD_FILES_BASE + dir)
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
	    output += "<p>" + str(e) + "</p>"
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
