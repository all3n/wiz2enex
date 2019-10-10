#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
# Copyright © 2019 all3n
# Distributed under terms of the MIT license.

"""
wiz export enex
"""
import os
import codecs
import os
import re
import sqlite3
import zipfile
import xml.dom.minidom as minidom
import xml.etree.ElementTree as ET
from datetime import datetime

def CDATA(text=None):
    element = ET.Element('![CDATA[')
    element.text = text
    return element

ET._original_serialize_xml = ET._serialize_xml

def _serialize_xml(write, elem, qnames, namespaces,short_empty_elements, **kwargs):

    if elem.tag == '![CDATA[':
        #write("\n<{}{}]]>\n".format(elem.tag, elem.text))
        write("<%s%s]]>" % (elem.tag, elem.text))
        if elem.tail:
            write(ET._escape_cdata(elem.tail))
    else:
        return ET._original_serialize_xml(write, elem, qnames, namespaces,short_empty_elements, **kwargs)

ET._serialize_xml = ET._serialize['xml'] = _serialize_xml

class EnexNote(object):
    def __init__(self, title, content, created, updated, author):
        self.title = title
        self.content = content
        self.created = created
        self.updated = updated
        self.author = author

    def create_text(self, name, text):
        node = ET.Element(name)
        node.text = text
        return node

    def to_xml(self):
        note = ET.Element("note")
        note.append(self.create_text('title', self.title))
        content = ET.Element("content")
        content_tag = """<?xml version="1.0" encoding="UTF-8" standalone="no"?><!DOCTYPE en-note SYSTEM "http://xml.evernote.com/pub/enml2.dtd"><en-note>%s</en-note>""" % (self.content)
        content.append(CDATA(content_tag))
        note.append(content)
        note.append(self.create_text('created', self.created))
        note.append(self.create_text('updated', self.updated))

        attr_node = ET.Element("note-attributes")

        attr_node.append(self.create_text("latitude","39.98448788609160"))
        attr_node.append(self.create_text("longitude","116.48423680726793"))
        attr_node.append(self.create_text("altitude","48.34932327270508"))
        attr_node.append(self.create_text("author", self.author))
        attr_node.append(self.create_text("source","desktop.mac"))

        note.append(attr_node)
        return note



class EnexExport(object):
    defaultEncoding = 'utf-8'
    def __init__(self):
        self.root = ET.Element("en-export")
        nowtime = datetime.now().strftime("%Y%m%dT%H%M%SZ")
        self.root.set("export-date", nowtime)
        self.root.set("application", "Evernote/Windows")
        self.root.set("version", "6.x")


    def add_note(self, title, content, created, updated, author):
        note = EnexNote(title, content, created, updated, author)
        self.root.append(note.to_xml())

    def export(self, f):
        xml_header = "<?xml version=\"1.0\" encoding=\"utf-8\"?>"
        doctype = "<!DOCTYPE en-export SYSTEM \"http://xml.evernote.com/pub/evernote-export2.dtd\">"
        rough_string = ET.tostring(self.root, self.defaultEncoding)
        #reparsed = minidom.parseString(rough_string)
        #return doctype + str(reparsed.toprettyxml(indent=" " , encoding=self.defaultEncoding))
        with open(f, "w") as wf:
            wf.write(xml_header + doctype + rough_string.decode('utf-8'))

def is_email(str):
    emailRegex = r'^[a-zA-Z0-9_-]+(\.[a-zA-Z0-9_-]+){0,4}@[a-zA-Z0-9_-]+(\.[a-zA-Z0-9_-]+){0,4}$'
    flag = re.match(emailRegex, str)
    return flag

def find_account():
    os.environ['HOME']
    os.path.expandvars('$HOME')
    homedir = os.path.expanduser('~')
    dirs = os.listdir(homedir + '/.wiznote')
    acc = [d for d in dirs if is_email(d)]
    return acc

def data_location(acc):
    return os.path.expanduser('~') + '/.wiznote/' + acc + '/data/'

def read_from_db(dbname, sql):
    mydb = sqlite3.connect(dbname)
    cursor = mydb.cursor()
    cursor.execute(sql)
    table = cursor.fetchall()
    return table


if __name__ == '__main__':
    accounts = find_account()
    for acc in accounts:
        ee = EnexExport()
        data_path = data_location(acc)
        db_file = os.path.join(data_path, 'index.db')
        fetch_sql = "select DOCUMENT_GUID, DOCUMENT_TITLE, DOCUMENT_LOCATION, DOCUMENT_URL, DT_CREATED,DT_MODIFIED from WIZ_DOCUMENT"
        notes = read_from_db(db_file, fetch_sql)
        for hash_val, notetitle, location, url, created, modified in notes:
            datec = datetime.strptime(created,  "%Y-%m-%d %H:%M:%S").strftime("%Y%m%dT%H%M%SZ")
            datem = datetime.strptime(modified, "%Y-%m-%d %H:%M:%S").strftime("%Y%m%dT%H%M%SZ")
            note_file = os.path.join(data_path, 'notes', '{'+hash_val+'}')
            zf = zipfile.ZipFile(note_file)
            fname = zf.namelist()[0]
            content = zf.open(fname).read().decode('utf-8')
            ee.add_note(notetitle, content, datec, datem, acc)
        ee.export("%s.enex" % acc)
