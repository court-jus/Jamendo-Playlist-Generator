#!/usr/bin/env python

#from lxml import etree
import xml.sax
import signal
import pdb
import sys
import optparse
import json

in_artist = None
in_album = None
tagged_albums = {
    'piano' : [],
    'blues' : [],
    }

class BreakHandler(object):
    def __init__(self, emphatic = 9):
        self._count = 0
        self._enabled = False
        self._emphatic = emphatic
        self._oldhandler = None

    def _reset(self):
        self._count = 0
    def enable(self):
        if not self._enabled:
            self._reset()
            self._enabled = True
            self._oldhandler = signal.signal(signal.SIGINT, self)
    def disable(self):
        if self._enabled:
            self._enabled = False
            signal.signal(signal.SIGINT, self._oldhandler)
            self._oldhandler = None
    def __call__(self, signame, sf):
        self._count += 1
        if self._count >= self._emphatic:
            self.disable()
        return
    def __del__(self):
        self.disable()
    @property
    def count(self):
        return self._count
    @property
    def trapped(self):
        return self._count > 0

def do_something_with_data(data):
    global in_artist, in_album, tagged_albums
    if data.tag == "artist":
        in_artist = data.findtext('id')
        #print "ARTIST : ", in_artist
    if data.tag == "album":
        in_album = data.findtext('id')
        #print "ALBUM : ", in_album
    if data.tag == "tag":
        tag = data.findtext('idstr')
        if tag in tagged_albums.keys():
            tagged_albums[tag].append((in_artist, in_album))
            print "hit",tag
    #print "DEBUG",data

def process_xml_iterative(xml_file, bh):
    iterator = iter(etree.iterparse(xml_file, ('start',), encoding = 'UTF-8'))
    while not bh.trapped:
        try:
            event, element = iterator.next()
        except (etree.XMLSyntaxError,),e:
            print "SYNTAX ERROR"
            continue
        except StopIteration:
            break
        except KeyboardInterrupt:
            break
        else:
            do_something_with_data(element)
            element.clear()
            del element

class MyGrabber(xml.sax.handler.ContentHandler):
    def __init__(self, tags = ['piano', 'blues']):
        #self._bh = BreakHandler()
        #self._bh.enable()
        self.intag = []
        self.artistcount = 0
        self.in_artist = None
        self.in_album = None
        self.in_track = None
        self.track_data = {}
        self.tagged_albums = dict([(tag,[]) for tag in tags])
        self.tagged_tracks = {}
    def startElement(self, name, attrs):
        self.intag.append(name)
    def endElement(self, name):
        assert self.intag[-1] == name
        self.intag = self.intag[:-1]
        if name == "track":
            self.track_data = {}
    def characters(self, content):
        if self.intag[-1] == "id" and self.intag[-2] == "artist":
            self.artistcount += 1
            sys.stderr.write("%s\r" % (self.artistcount,))
            self.in_artist = content
        elif self.intag[-1] == "id" and self.intag[-2] == "album":
            self.in_album = content
        elif self.intag[-1] == "id" and self.intag[-2] == "track":
            self.in_track = content
        elif self.intag[-2] == "track":
            self.track_data[self.intag[-1]] = content
        elif self.intag[-1] == "idstr" and self.intag[-2] == "tag":
            self.tagged_tracks.setdefault(content, []).append([self.in_artist, self.in_album, self.in_track])
            if content in self.tagged_albums.keys():
                self.tagged_albums[content].append([self.in_artist, self.in_album, self.in_track])

class Analyser(object):
    def __init__(self, data):
        self.data = data
        self.cumulated = self.cumulate()
    def cumulate(self):
        keys = self.data.keys()
        fkey = keys[0]
        okeys = keys[1:]
        result = []
        for album_tuple in self.data[fkey]:
            if not all([album_tuple in self.data[okey] for okey in okeys]):
                continue
            result.append(album_tuple)
        return result
    def __unicode__(self):
        MP3STREAM = "http://api.jamendo.com/get2/stream/track/redirect/?id=%s&streamencoding=mp31"
        OGGSTREAM = "http://api.jamendo.com/get2/stream/track/redirect/?id=%s&streamencoding=ogg2"
        TRACKDATA = "http://www.jamendo.com/fr/track/%s"
        return u"\n".join([MP3STREAM % (id_track,) for id_artist, id_album, id_track in self.cumulated])
    def __str__(self):
        return unicode(self)
if __name__ == "__main__":
    parser = optparse.OptionParser()
    option, tags = parser.parse_args()
    xml_file = "dbdump_artistalbumtrack.xml"
    grabber = MyGrabber(tags = tags)
    if len(tags) == 0:
        sys.stderr.write("You need to tell me what tags you're looking for\n")
    else:
        try:
            xml.sax.parse(xml_file, grabber)
        except KeyboardInterrupt:
            pass
        data = grabber.tagged_albums
        with open("jamendo.json", "wb") as fp:
            json.dump(grabber.tagged_tracks, fp, indent = 4)
        for tag in tags:
            sys.stderr.write("%s - %s\n" % (tag, len(data.get(tag, [])),))
        analyser = Analyser(data)
        sys.stderr.write("%s Cumulated\n" % (len(analyser.cumulated)))
        print analyser
