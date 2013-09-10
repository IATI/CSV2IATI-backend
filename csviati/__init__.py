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
import codes
from functools import wraps
from xml.etree.cElementTree import Element, ElementTree
from flask import Flask, render_template, flash, request, Markup, jsonify, current_app
app = Flask(__name__)

UPLOAD_FILES_BASE = os.path.dirname(__file__) + '/'

def jsonp(func):
    """Wraps JSONified output for JSONP requests."""
    @wraps(func)
    def decorated_function(*args, **kwargs):
        callback = request.args.get('callback', False)
        if callback:
            data = str(func(*args, **kwargs).data)
            content = str(callback) + '(' + data + ')'
            mimetype = 'application/javascript'
            return current_app.response_class(content, mimetype=mimetype)
        else:
            return func(*args, **kwargs)
    return decorated_function

class Error(Exception):
    def __init__(self, value):
        self.value = value

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

def append_recursive(key, val, parent):
    key = Element(key)
    empty = True
    for attrib, attrib_value in val.items():
        if isinstance(attrib_value, dict):
            empty = append_recursive(attrib, attrib_value, key) and empty
        elif (attrib == 'text'):
            if unicode(attrib_value) != '':
                key.text = attrib_value
                empty = False
        else:
            if unicode(attrib_value) != '':
                key.set(attrib, unicode(attrib_value))
                empty = False
    if not empty:
        parent.append(key)
    return empty

# Process the data created in parse_csv()
def create_IATI_xml(iatidata, dir, o):
    #iatidata contains the activities
    #o contains the organisation data
    output = ''
    node = Element('iati-activities')
    node.set("version", "1.02")
    current_datetime = datetime.now().replace(microsecond=0).isoformat()
    node.set("generated-datetime",current_datetime)
    character_encoding = o["data-encoding"]
    for activity in iatidata:
        #for each activity, create one <iati-activity>
        a = Element("iati-activity")
        a.set("xml:lang", o["lang"])
        a.set("default-currency", o["default-currency"])
        a.set("last-updated-datetime", current_datetime)
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
                append_recursive(key,val,a)
    doc = ElementTree(node)
    XMLfile = str(time.time()) + '.xml'
    XMLfilename = dir + '/' + XMLfile
    XMLabsfilename = UPLOAD_FILES_BASE + dir + '/' + XMLfile
    doc.write(XMLabsfilename)
    XMLfilename_html = request.url_root + XMLfilename
    return XMLfilename_html

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
                             {
                                 "project ID" = "PROJECT_1",
                                 "title" = "My project title",
                                 "sector_name" = "First sector"
                             },
                             {
                                 "project ID" = "PROJECT_1",
                                 "title" = "My project title",
                                 "sector_name" = "Second sector"
                             }
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
    # m contains the mapping data
    # o contains the organisation data

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
                            raise Error("%s" % value.message)
                        #iati_field contains the name of the IATI field this dimension should output.
                        if ((not already_got_project_data) or (iati_field == multiple_field)):
                            fielddata = get_field_data(iati_field, field, m, line, character_encoding)
                            if (fielddata):
                                linedata.append(fielddata)
                except KeyError, e:
                    type, value, tb = sys.exc_info()
                    raise Error("ERROR: No such field: %s" % value.message)
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
                        raise Error("%s" % value.message)
                    #iati_field contains the name of the IATI field this dimension should output.

                    fielddata = get_field_data(iati_field, field, m, line, character_encoding)
                    
                    # only append this to the data if the field is not empty
                    if (fielddata):
                        linedata.append(fielddata)
                iatidata.append(linedata)
            except KeyError, e:
                type, value, tb = sys.exc_info()
                raise Error("ERROR: No such field: %s" % value.message)
    flash("Parsed files", 'good')
    return create_IATI_xml(iatidata, dir, o)
 
def format_field_value(fields, part, line, character_encoding, field=None):
    if not field:
        field = fields[part]
    if field["datatype"] == "constant":
        return field["constant"]
    part_column = field["column"]
    # replace [newline] on part_column with \n -- this is as a consequence of a fix in the modeleditor
    part_column = newline_fix(part_column)
    out = ''
    if ((field.has_key("datatype")) and (field == 'float')):
        try:
            out = float(line[makePreviousEncoding(part_column, character_encoding)])
            if (str(float(line[makePreviousEncoding(part_column, character_encoding)])) == '-0.0'):
                out = '0'
        except:
            out = '0'

        out = (makeUnicode(line[makePreviousEncoding(part_column,encoding=character_encoding)].strip().replace(field["stripchars"], ""),encoding=character_encoding))
    elif (field.has_key("text-transform-type")):
        thedata = makeUnicode(line[makePreviousEncoding(part_column, character_encoding)], encoding=character_encoding).strip()
        if (field["text-transform-type"] == "date"):
            text_transform_format = field["text-transform-format"]
            try:
                newdate = datetime.strptime(thedata, text_transform_format).strftime("%Y-%m-%d")
                out = str(newdate)
            except ValueError, e:
                #TODO log this somehow else
                #output += "Failed to convert date:", e
                pass
        elif (field["text-transform-type"] == "multiply"):
            try:
                out = float(thedata)*float(field["text-transform-format"])
            except ValueError:
                out = ''
        elif (field["text-transform-type"] == "text-before"):
            out = field["text-transform-format"] + thedata 
        elif (field["text-transform-type"] == "text-after"):
            out = thedata + field["text-transform-format"]
        elif (field["text-transform-type"] == "field-after"):
            out = thedata + format_field_value(fields, field["text-transform-format"], line, character_encoding)
        elif (field["text-transform-type"] == "crs-country-code"):
            try:
                out = codes.crs_country[thedata][0] 
            except KeyError:
                out = ''
        elif (field["text-transform-type"] == "crs-country-name"):
            try:
                out = codes.crs_country[thedata][1] 
            except KeyError:
                out = ''
        elif (field["text-transform-type"] == "crs-region-code"):
            if thedata in codes.crs_region:
                return thedata
        elif (field["text-transform-type"] == "crs-region-name"):
            try:
                out = codes.crs_region[thedata]
            except KeyError:
                out = '' 
        elif (field["text-transform-type"] == "crs-tied-status"):
            usd_commitment = thedata
            usd_ammountuntied = makeUnicode(line[makePreviousEncoding(field["column2"], character_encoding)], encoding=character_encoding).strip()
            usd_ammountpartialtied = makeUnicode(line[makePreviousEncoding(field["column3"], character_encoding)], encoding=character_encoding).strip()
            # Copied from DCs PHP code
            if usd_commitment:
                if usd_commitment == usd_ammountuntied:
                    out = 5
                else:
                    out = ''
            elif usd_ammountpartialtied:
                out = 3;
            else:
                out = 4;
    else:
        # this is the bit that almost always does the work
        try:
            out = (makeUnicode(line[makePreviousEncoding(part_column,character_encoding)],encoding=character_encoding))
        except KeyError:
            if part_column == '':
                out = ''

    if field.has_key("alternatives"):
        for n, alternative in field["alternatives"].items():
            if out:
                break 
            out = format_field_value(fields, None, line, character_encoding, field=alternative)

    del part_column
    return out

def get_fields_recursive(fields, line, character_encoding):
    out = {}
    for part in fields:
        # in the dimension mapping, the variable 'part' is called 'field'. Should probably make this more consistent...
        if part.startswith('virtual_'):
            continue
        if (fields[part]["datatype"] == 'compound'):
            out[part] = get_fields_recursive(fields[part]["fields"], line, character_encoding) 
        elif (fields[part]["datatype"] == 'constant'):
            out[part] = fields[part]["constant"]
        else:
            out[part] = format_field_value(fields, part, line, character_encoding)
    return out

def get_field_data(iati_field, field, m, line, character_encoding):
    fielddata= {}
    #fielddata = the hash to contain all of this dimension's data
    fielddata_empty_flag = False
   
    # if the dimension (field) is of datatype compound:
    if m[field]["datatype"] == "compound":
        fielddata[iati_field] = get_fields_recursive(m[field]["fields"], line, character_encoding)
                    
    # BJWEBB fielddata_empty_flag removed
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
        output = "ERROR: The server couldn't fulfill the request."
        output += "Error code: ", e.code
        raise Error(output)
    except urllib2.URLError, e:
        output = "ERROR: Could not reach the server."
        output += "Reason: ", e.reason
        raise Error(output)

# Receive the files as inputs from the command line
def get_files():
    try:
        csvfile = request.form['csv_url']
        modelfile = request.form['model_url']
    except KeyError:
        try:
            csvfile = request.args['csv_url']
            modelfile = request.args['model_url']
        except KeyError:
            raise Error("Required arguments: csv_url model_url")
    dir = 'static/' + str(date.today())
#output = os.path.abspath(UPLOAD_FILES_BASE + dir)
    if not os.path.exists(UPLOAD_FILES_BASE + dir):
        try:
            os.makedirs(UPLOAD_FILES_BASE + dir)
        except Exception, e:
            flash(("Failed:", e),'bad')
            raise Error("Couldn't create directory")
    try:
        flash("Saving CSV file...", 'notice')
        save_file(csvfile, 'csv', dir)
        flash("Saving mapping file...", 'notice')
        save_file(modelfile, 'json', dir)
    except Exception, e:
        flash("Couldn't save files.", 'bad')
        raise Error("<p>" + str(e) + "</p>"
            + "<p>Files need to be provided as full URLs.</p>"
            + "<p>You provided the following URLs:"
            + "<p>CSV file: " + csvfile + "</p>"
            + "<p>Model file: " + modelfile + "</p>")
    else:
        flash("Saved files", 'good')
        return parse_csv(dir) 

@app.route("/", methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        return doConversion()
    else:
        return showPostForm()

@app.route("/json", methods=['GET', 'POST'])
@jsonp
def index_json():
    try:
        return jsonify(result=get_files())
    except Error as e:
        return jsonify(error=e.value)

def doConversion():
    output = ''
    try:
        url = get_files()
        output += "<p>IATI-XML file saved to <a href=\"" + url  + "\">" + url + "</a></p>"
    except Error as e:
        output += e.value
    return render_template('output.html', output=Markup(output))

def showPostForm():
    return render_template('form.html')

app.secret_key = os.urandom(24)

if __name__ == '__main__':
    if (len(sys.argv) > 1):
        port = int(sys.argv[1])
        app.run(debug=True,port=port)
    else:
        app.run(debug=True,port=5001)
