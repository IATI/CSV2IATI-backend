International Aid Transparency Initiative CSV Conversion tool
=============================================================

The scripts in this repository transform data from a CSV spreadsheet
into IATI-XML data. This requires two components:

* Data -- A flat CSV file
* Mapping -- A JSON mapping file, which describes how the CSV file should be related to the IATI Standard

Running the script
------------------

The script takes two arguments: the source CSV file and the mapping. 
These must be provided as full URLs, even if they are only on your computer. For example:

    $ python run.py file:///home/YOUR_USER_NAME/PATH_TO_CSV_CONVERSION_TOOL/testdata/csv.csv file:///home/YOUR_USER_NAME/PATH_TO_CSV_CONVERSION_TOOL/testdata/json.json

The data will be output to PATH_TO_CONVERSION_TOOL/temp/TODAY'S_DATE/IATI.xml

JSON mapping file
-----------------

There are two sections in the JSON mapping file:

* `organisation`
* `mapping` 

*Organisation section*

The mapping section should contain:

* The reporting organisation data (``reporting-org``)
* The default currency (``default-currency``)
* The default language (``lang``)

** Example: **

::
    "organisation": {
        "reporting-org": {
            "text": "Oxfam GB",
            "ref": "GB-CHC-202918",
            "type": "21"
        },
        "default-currency": "GBP",
        "lang": "en"
    }
::

*Mapping section*

In the JSON mapping file, you create one element per object that you 
want to represent.

* Each object must have a unique name.
* Each object must define the IATI field it relates to (``iati_field``)
* Each object must define whether the source data for the output is a ``column`` in the CSV file or a ``constant`` if it is the same value for all entries (``type``)
* Objects can also have *prefixes* (e.g., if the source data contains the project ID you want to use in the ``iati-identifier`` IATI field, you would prefix it with the reporting organisation's reference. (``prefix``)
* Objects can also be more complicated if they have attributes. In this case you set the ``type`` to ``compound`` and create a series of ``fields`` within that object.

** Example: **

    "mapping": {
        "title": {
            "iati_field": "title",
            "column": "Title Project",
            "default_value": "",
            "constant": "",
            "type": "column"
        },
        "iati-identifier": {
            "iati_field": "iati-identifier",
            "column": "Project ID",
            "default_value": "",
            "constant": "",
            "type": "column",
            "prefix":"GB-CHC-202918-"
        },
        "recipient-country": {
            "iati_field": "recipient-country",
            "fields": {
                "text": {
                    "type": "column",
                    "column": "Loc of Impact"
                },
                "code": {
                    "type": "column",
                    "column": "ISO CODE"
                }
            },
            "type": "compound"
        }
    }

