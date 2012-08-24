International Aid Transparency Initiative CSV Conversion tool
=============================================================

The scripts in this repository transform data from a CSV spreadsheet
into IATI-XML data. This requires two components:

* Data -- A flat CSV file
* Mapping -- A JSON mapping file, which describes how the CSV file should be related to the IATI Standard

Installation
------------

Clone the repository:

::

    $ git clone git://github.com/markbrough/CSV-IATI-Converter.git


Change into the directory and create a virtual environment (``virtualenv``)

::

    $ cd CSV-IATI-Converter
    $ virtualenv --no-site-packages ./pyenv

Now activate the environment:

::

    $ source ./pyenv/bin/activate

Install dependencies:

::

    $ pip install -r requirements.txt


If you're running locally, you can stop here and jump to "Running the script". If you're deploying to an Apache server, keep reading...

Install mod_wsgi

::
    
    $ apt-get install libapache2-mod-wsgi

Copy wsgi.py from the main directory to the appropriate folder in your web server directory, e.g. ``/var/www/csviati``

::
    
    $ cp wsgi.py /var/www/csviati/wsgi.py

Edit the file to make sure the paths are correct for your web server


Create a symlink from this folder to the static files folder in your installation directory, so that they can be accessed by the web server:

::
    
    $ ln -s /PATH_TO_YOUR_CSVCONVERTER_FILES/CSV-IATI-Converter/csviati/static /var/www/csviati/static


Set up your Apache configuration files. You can do this easily by copying the default file:

::
    
    $ cd /etc/apache2/sites-available/
    $ cp default csviati

Then edit the configuration to something like:

::
    
    <VirtualHost *:80>
        ServerAdmin webmaster@localhost

        DocumentRoot /var/www
        ErrorLog /var/log/apache2/error.log

        # Possible values include: debug, info, notice, warn, error, crit,
        # alert, emerg.
        LogLevel debug

        CustomLog /var/log/apache2/access.log combined

        WSGIDaemonProcess csviati user=user__www group=group1 threads=5
        WSGIScriptAlias /csviati /var/www/csviati/wsgi.py

        Alias /csviati/static/ "/var/www/csviati/static/"


        <Directory /var/www/csviati>
            Options Indexes FollowSymLinks Multiviews
            WSGIProcessGroup csviati
            WSGIApplicationGroup %{GLOBAL}
            Order deny,allow
            Allow from all
        </Directory>

    </VirtualHost>

Disable the default site and enable your new site

::
    
    $ sudo a2dissite default && a2ensite csviati

Reload Apache:

::
    
    $ sudo /etc/init.d/apache2 reload


Running the script
------------------

The script takes two arguments: the source CSV file and the mapping. 
These must be provided as full URLs, even if they are only on your computer. For example:

::

    $ python run.py file:///home/YOUR_USER_NAME/PATH_TO_CSV_CONVERSION_TOOL/testdata/csv.csv file:///home/YOUR_USER_NAME/PATH_TO_CSV_CONVERSION_TOOL/testdata/json.json

The data will be output to PATH_TO_CONVERSION_TOOL/temp/TODAY'S_DATE/IATI.xml

JSON mapping file
-----------------

There are two sections in the JSON mapping file:

* `organisation`
* `mapping` 

**Organisation section**

The mapping section should contain:

* The reporting organisation data (``reporting-org``)
* The default currency (``default-currency``)
* The default language (``lang``)
* The data structure (``data-structure``)

*Example:*
::

    "organisation": {

        "reporting-org": {
            "text": "United States Agency for International Development",
            "ref": "US-1",
            "type": "10"
        },
        "default-currency": "USD",
        "lang": "en",
        "contact-info": {
            "person-name": "",
            "telephone": "",
            "email": "",
            "address": ""
        },
        "data-encoding": "utf-8",
        "data-structure": {
            "multiple": ""
        }

    }


**Mapping section**

In the JSON mapping file, you create one element per object that you 
want to represent.

* Each object must have a unique name.
* Each object must define the IATI field it relates to (``iati-field``)
* Each object must define whether the source data for the output is a ``column`` in the CSV file or a ``constant`` if it is the same value for all entries (``datatype``)
* Objects can also have *prefixes* (e.g., if the source data contains the project ID you want to use in the ``iati-identifier`` IATI field, you would prefix it with the reporting organisation's reference. (``prefix``)
* Objects can also be more complicated if they have attributes. In this case you set the ``datatype`` to ``compound`` and create a series of ``fields`` within that object.

*Example:*
::

    "mapping": {

        "iati-identifier": {
            "datatype": "compound",
            "iati-field": "iati-identifier",
            "label": "IATI Identifier",
            "fields": {
                "text": {
                    "datatype": "column",
                    "column": "donor_project_number"
                }
            }
        },
        "title": {
            "datatype": "compound",
            "iati-field": "title",
            "label": "Title",
            "fields": {
                "text": {
                    "datatype": "column",
                    "column": "project_title"
                }
            }
        },
        "description": {
            "datatype": "compound",
            "iati-field": "description",
            "label": "Description",
            "fields": {
                "text": {
                    "datatype": "column",
                    "column": "description"
                }
            }
        },
        "activity-date-start": {
            "datatype": "compound",
            "iati-field": "activity-date",
            "label": "Activity Start Date",
            "fields": {
                "type": {
                    "datatype": "constant",
                    "constant": "start-planned"
                },
                "iso-date": {
                    "datatype": "constant",
                    "constant": "2010-01-01"
                },
                "text": {
                    "datatype": "constant",
                    "constant": "2010-01-01"
                }
            }
        },
        "activity-date-end": {
            "datatype": "compound",
            "iati-field": "activity-date",
            "label": "Activity End Date",
            "fields": {
                "type": {
                    "datatype": "constant",
                    "constant": "planned-end"
                },
                "iso-date": {
                    "datatype": "constant",
                    "constant": "2010-12-31"
                },
                "text": {
                    "datatype": "constant",
                    "constant": "2010-12-31"
                }
            }
        },
        "recipient-country": {
            "datatype": "compound",
            "iati-field": "recipient-country",
            "label": "Recipient Country",
            "fields": {
                "text": {
                    "datatype": "column",
                    "column": "recipient_country"
                },
                "code": {
                    "datatype": "constant",
                    "constant": "TZ"
                }
            }
        },
        "funding-organisation": {
            "datatype": "compound",
            "iati-field": "participating-org",
            "label": "Funding Organisation",
            "fields": {
                "role": {
                    "datatype": "constant",
                    "constant": "funding"
                },
                "text": {
                    "datatype": "constant",
                    "constant": "United States"
                },
                "ref": {
                    "datatype": "constant",
                    "constant": "US"
                },
                "type": {
                    "datatype": "constant",
                    "constant": "10"
                }
            }
        },
        "extending-organisation": {
            "datatype": "compound",
            "iati-field": "participating-org",
            "label": "Extending Organisation",
            "fields": {
                "role": {
                    "datatype": "constant",
                    "constant": "extending"
                },
                "text": {
                    "datatype": "constant",
                    "constant": "USAID"
                },
                "ref": {
                    "datatype": "constant",
                    "constant": "US-1"
                },
                "type": {
                    "datatype": "constant",
                    "constant": "10"
                }
            }
        },
        "implementing-organisation": {
            "datatype": "compound",
            "iati-field": "participating-org",
            "label": "Implementing Organisation",
            "fields": {
                "role": {
                    "datatype": "constant",
                    "constant": "implementing"
                },
                "text": {
                    "datatype": "column",
                    "column": "channel_name"
                },
                "ref": {
                    "datatype": "column",
                    "column": "channel_code"
                },
                "type": {
                    "datatype": "column",
                    "column": "channel_code"
                }
            }
        },
        "sectors": {
            "datatype": "compound",
            "iati-field": "sector",
            "label": "Sectors",
            "fields": {
                "text": {
                    "datatype": "column",
                    "column": "purpose_code"
                },
                "code": {
                    "datatype": "column",
                    "column": "purpose_code"
                },
                "vocab": {
                    "datatype": "constant",
                    "constant": "DAC"
                }
            }
        },
        "transaction": {
            "datatype": "transaction",
            "iati-field": "transaction",
            "label": "Transactions",
            "tdatafields": {
                "transaction_type": {
                    "label": "Transaction type",
                    "iati-field": "transaction-type",
                    "fields": {
                        "text": {
                            "datatype": "constant",
                            "constant": "Disbursement"
                        },
                        "code": {
                            "datatype": "constant",
                            "constant": "D"
                        }
                    }
                },
                "value": {
                    "label": "Transaction value",
                    "iati-field": "value",
                    "fields": {
                        "text": {
                            "datatype": "column",
                            "column": "abs_amt_extended"
                        },
                        "value-date": {
                            "datatype": "constant",
                            "constant": "2010-01-01"
                        }
                    }
                },
                "transaction-date": {
                    "label": "Transaction Date",
                    "iati-field": "transaction-date",
                    "fields": {
                        "iso-date": {
                            "datatype": "constant",
                            "constant": "2010-01-01"
                        },
                        "text": {
                            "datatype": "constant",
                            "constant": "2010-01-01"
                        }
                    }
                }
            }
        },
        "flow-type": {
            "datatype": "compound",
            "iati-field": "default-flow-type",
            "label": "User field: flow-type",
            "fields": {
                "code": {
                    "datatype": "column",
                    "column": "flow_type"
                },
                "text": {
                    "datatype": "column",
                    "column": "flow_type"
                }
            }
        },
        "finance-type": {
            "datatype": "compound",
            "iati-field": "default-finance-type",
            "label": "User field: finance-type",
            "fields": {
                "code": {
                    "datatype": "column",
                    "column": "finance_type"
                },
                "text": {
                    "datatype": "column",
                    "column": "finance_type"
                }
            }
        },
        "aid-type": {
            "datatype": "compound",
            "iati-field": "default-aid-type",
            "label": "User field: aid-type",
            "fields": {
                "code": {
                    "datatype": "column",
                    "column": "dac_typology"
                },
                "text": {
                    "datatype": "column",
                    "column": "dac_typology"
                }
            }
        },
        "activity-status": {
            "datatype": "compound",
            "iati-field": "activity-status",
            "label": "User field: activity-status",
            "fields": {
                "code": {
                    "datatype": "constant",
                    "constant": "2"
                },
                "text": {
                    "datatype": "constant",
                    "constant": "Implementation"
                }
            }
        },
        "commitments": {
            "datatype": "transaction",
            "iati-field": "transaction",
            "label": "User field: commitments",
            "tdatafields": {
                "transaction-type": {
                    "label": "Transaction Type",
                    "iati-field": "transaction-type",
                    "fields": {
                        "text": {
                            "datatype": "constant",
                            "constant": "Commitment"
                        },
                        "code": {
                            "datatype": "constant",
                            "constant": "C"
                        }
                    }
                },
                "value": {
                    "label": "Transaction Value",
                    "iati-field": "value",
                    "fields": {
                        "text": {
                            "datatype": "column",
                            "column": "abs_commitments"
                        },
                        "value-date": {
                            "datatype": "constant",
                            "constant": "2010-01-01"
                        }
                    }
                },
                "transaction-date": {
                    "label": "Transaction Date",
                    "iati-field": "transaction-date",
                    "fields": {
                        "iso-date": {
                            "datatype": "constant",
                            "constant": "2010-01-01"
                        },
                        "text": {
                            "datatype": "constant",
                            "constant": "2010-01-01"
                        }
                    }
                }
            }
        }

    }

