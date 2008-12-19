#!/usr/bin/env python

# Produces a report on NEW and BYHAND packages
# Copyright (C) 2001, 2002, 2003, 2005, 2006  James Troup <james@nocrew.org>

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

################################################################################

# <o-o> XP runs GCC, XFREE86, SSH etc etc,.,, I feel almost like linux....
# <o-o> I am very confident that I can replicate any Linux application on XP
# <willy> o-o: *boggle*
# <o-o> building from source.
# <o-o> Viiru: I already run GIMP under XP
# <willy> o-o: why do you capitalise the names of all pieces of software?
# <o-o> willy: because I want the EMPHASIZE them....
# <o-o> grr s/the/to/
# <willy> o-o: it makes you look like ZIPPY the PINHEAD
# <o-o> willy: no idea what you are talking about.
# <willy> o-o: do some research
# <o-o> willy: for what reason?

################################################################################

import copy, glob, os, stat, sys, time
import apt_pkg
import cgi
from daklib import queue
from daklib import utils
from daklib.dak_exceptions import *

Cnf = None
Upload = None
direction = []
row_number = 0

################################################################################

def usage(exit_code=0):
    print """Usage: dak queue-report
Prints a report of packages in queue directories (usually new and byhand).

  -h, --help                show this help and exit.
  -n, --new                 produce html-output
  -s, --sort=key            sort output according to key, see below.
  -a, --age=key             if using sort by age, how should time be treated?
                            If not given a default of hours will be used.

     Sorting Keys: ao=age,   oldest first.   an=age,   newest first.
                   na=name,  ascending       nd=name,  descending
                   nf=notes, first           nl=notes, last

     Age Keys: m=minutes, h=hours, d=days, w=weeks, o=months, y=years

"""
    sys.exit(exit_code)

################################################################################

def plural(x):
    if x > 1:
        return "s"
    else:
        return ""

################################################################################

def time_pp(x):
    if x < 60:
        unit="second"
    elif x < 3600:
        x /= 60
        unit="minute"
    elif x < 86400:
        x /= 3600
        unit="hour"
    elif x < 604800:
        x /= 86400
        unit="day"
    elif x < 2419200:
        x /= 604800
        unit="week"
    elif x < 29030400:
        x /= 2419200
        unit="month"
    else:
        x /= 29030400
        unit="year"
    x = int(x)
    return "%s %s%s" % (x, unit, plural(x))

################################################################################

def sg_compare (a, b):
    a = a[1]
    b = b[1]
    """Sort by have note, time of oldest upload."""
    # Sort by have note
    a_note_state = a["note_state"]
    b_note_state = b["note_state"]
    if a_note_state < b_note_state:
        return -1
    elif a_note_state > b_note_state:
        return 1

    # Sort by time of oldest upload
    return cmp(a["oldest"], b["oldest"])

############################################################

def sortfunc(a,b):
    for sorting in direction:
        (sortkey, way, time) = sorting
        ret = 0
        if time == "m":
            x=int(a[sortkey]/60)
            y=int(b[sortkey]/60)
        elif time == "h":
            x=int(a[sortkey]/3600)
            y=int(b[sortkey]/3600)
        elif time == "d":
            x=int(a[sortkey]/86400)
            y=int(b[sortkey]/86400)
        elif time == "w":
            x=int(a[sortkey]/604800)
            y=int(b[sortkey]/604800)
        elif time == "o":
            x=int(a[sortkey]/2419200)
            y=int(b[sortkey]/2419200)
        elif time == "y":
            x=int(a[sortkey]/29030400)
            y=int(b[sortkey]/29030400)
        else:
            x=a[sortkey]
            y=b[sortkey]
        if x < y:
            ret = -1
        elif x > y:
            ret = 1
        if ret != 0:
            if way < 0:
                ret = ret*-1
            return ret
    return 0

############################################################

def header():
    print """<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"
"http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="de" lang="de">
  <head>
    <meta http-equiv="content-type" content="text/xhtml+xml; charset=utf-8" />
    <link type="text/css" rel="stylesheet" href="style.css" />
    <link rel="shortcut icon" href="http://www.debian.org/favicon.ico" />
    <title>
      Debian NEW and BYHAND Packages
    </title>
  </head>
  <body id="NEW">
    <div id="logo">
      <a href="http://www.debian.org/">
        <img src="http://www.debian.org/logos/openlogo-nd-50.png"
        alt="debian logo" /></a>
      <a href="http://www.debian.org/">
        <img src="http://www.debian.org/Pics/debian.png"
        alt="Debian Project" /></a>
    </div>
    <div id="titleblock">

      <img src="http://www.debian.org/Pics/red-upperleft.png"
      id="red-upperleft" alt="corner image"/>
      <img src="http://www.debian.org/Pics/red-lowerleft.png"
      id="red-lowerleft" alt="corner image"/>
      <img src="http://www.debian.org/Pics/red-upperright.png"
      id="red-upperright" alt="corner image"/>
      <img src="http://www.debian.org/Pics/red-lowerright.png"
      id="red-lowerright" alt="corner image"/>
      <span class="title">
        Debian NEW and BYHAND Packages
      </span>
    </div>
    """

def footer():
    print "<p class=\"timestamp\">Timestamp: %s (UTC)</p>" % (time.strftime("%d.%m.%Y / %H:%M:%S", time.gmtime()))

    print """
    <div class="footer">
    <p>Hint: Age is the youngest upload of the package, if there is more than
    one version.<br />
    You may want to look at <a href="http://ftp-master.debian.org/REJECT-FAQ.html">the REJECT-FAQ</a>
      for possible reasons why one of the above packages may get rejected.</p>
      <p>
      <a href="http://validator.w3.org/check?uri=referer"><img src="http://www.w3.org/Icons/valid-xhtml10"
        alt="Valid XHTML 1.0 Strict" height="31" width="88" /></a>
      <a href="http://jigsaw.w3.org/css-validator/">
        <img style="border:0;width:88px;height:31px" src="http://jigsaw.w3.org/css-validator/images/vcss"
        alt="Valid CSS!" />
      </a>
      </p>
    </div> </body> </html>
    """

def table_header(type, source_count, total_count):
    print "<h1>Summary for: %s</h1>" % (type)
    print """
    <table class="NEW">
      <caption>
    """
    print "Package count in <strong>%s</strong>: <em>%s</em>&nbsp;|&nbsp; Total Package count: <em>%s</em>" % (type, source_count, total_count)
    print """
      </caption>
      <thead>
        <tr>
          <th>Package</th>
          <th>Version</th>
          <th>Arch</th>
          <th>Distribution</th>
          <th>Age</th>
          <th>Upload info</th>
          <th>Closes</th>
        </tr>
      </thead>
      <tbody>
    """

def table_footer(type):
    print "</tbody></table>"


def table_row(source, version, arch, last_mod, maint, distribution, closes, fingerprint, sponsor, changedby):

    global row_number

    trclass = "sid"
    for dist in distribution:
        if dist == "experimental":
            trclass = "exp"

    if row_number % 2 != 0:
        print "<tr class=\"%s even\">" % (trclass)
    else:
        print "<tr class=\"%s odd\">" % (trclass)

    print "<td class=\"package\">%s</td>" % (source)
    print "<td class=\"version\">"
    for vers in version.split():
        print "<a href=\"/new/%s_%s.html\">%s</a><br/>" % (source, utils.html_escape(vers), utils.html_escape(vers))
    print "</td>"
    print "<td class=\"arch\">%s</td>" % (arch)
    print "<td class=\"distribution\">"
    for dist in distribution:
        print "%s<br/>" % (dist)
    print "</td>"
    print "<td class=\"age\">%s</td>" % (last_mod)
    (name, mail) = maint.split(":")

    print "<td class=\"upload-data\">"
    print "<span class=\"maintainer\">Maintainer: <a href=\"http://qa.debian.org/developer.php?login=%s\">%s</a></span><br/>" % (utils.html_escape(mail), utils.html_escape(name))
    (name, mail) = changedby.split(":")
    print "<span class=\"changed-by\">Changed-By: <a href=\"http://qa.debian.org/developer.php?login=%s\">%s</a></span><br/>" % (utils.html_escape(mail), utils.html_escape(name))

    try:
        (login, domain) = sponsor.split("@")
        print "<span class=\"sponsor\">Sponsor: <a href=\"http://qa.debian.org/developer.php?login=%s\">%s</a></span>@debian.org<br/>" % (utils.html_escape(login), utils.html_escape(login))
    except:
        pass

    print "<span class=\"signature\">Fingerprint: %s</span>" % (fingerprint)
    print "</td>"

    print "<td class=\"closes\">"
    for close in closes:
        print "<a href=\"http://bugs.debian.org/cgi-bin/bugreport.cgi?bug=%s\">#%s</a><br/>" % (utils.html_escape(close), utils.html_escape(close))
    print "</td></tr>"
    row_number+=1

############################################################

def process_changes_files(changes_files, type):
    msg = ""
    cache = {}
    # Read in all the .changes files
    for filename in changes_files:
        try:
            Upload.pkg.changes_file = filename
            Upload.init_vars()
            Upload.update_vars()
            cache[filename] = copy.copy(Upload.pkg.changes)
            cache[filename]["filename"] = filename
        except:
            break
    # Divide the .changes into per-source groups
    per_source = {}
    for filename in cache.keys():
        source = cache[filename]["source"]
        if not per_source.has_key(source):
            per_source[source] = {}
            per_source[source]["list"] = []
        per_source[source]["list"].append(cache[filename])
    # Determine oldest time and have note status for each source group
    for source in per_source.keys():
        source_list = per_source[source]["list"]
        first = source_list[0]
        oldest = os.stat(first["filename"])[stat.ST_MTIME]
        have_note = 0
        for d in per_source[source]["list"]:
            mtime = os.stat(d["filename"])[stat.ST_MTIME]
            if Cnf.has_key("Queue-Report::Options::New"):
                if mtime > oldest:
                    oldest = mtime
            else:
                if mtime < oldest:
                    oldest = mtime
            have_note += (d.has_key("process-new note"))
        per_source[source]["oldest"] = oldest
        if not have_note:
            per_source[source]["note_state"] = 0; # none
        elif have_note < len(source_list):
            per_source[source]["note_state"] = 1; # some
        else:
            per_source[source]["note_state"] = 2; # all
    per_source_items = per_source.items()
    per_source_items.sort(sg_compare)

    entries = []
    max_source_len = 0
    max_version_len = 0
    max_arch_len = 0
    for i in per_source_items:
        maintainer = {}
        maint=""
        distribution=""
        closes=""
        fingerprint=""
        changeby = {}
        changedby=""
        sponsor=""
        last_modified = time.time()-i[1]["oldest"]
        source = i[1]["list"][0]["source"]
        if len(source) > max_source_len:
            max_source_len = len(source)
        arches = {}
        versions = {}
        for j in i[1]["list"]:
            if Cnf.has_key("Queue-Report::Options::New"):
                try:
                    (maintainer["maintainer822"], maintainer["maintainer2047"],
                    maintainer["maintainername"], maintainer["maintaineremail"]) = \
                    utils.fix_maintainer (j["maintainer"])
                except ParseMaintError, msg:
                    print "Problems while parsing maintainer address\n"
                    maintainer["maintainername"] = "Unknown"
                    maintainer["maintaineremail"] = "Unknown"
                maint="%s:%s" % (maintainer["maintainername"], maintainer["maintaineremail"])
                # ...likewise for the Changed-By: field if it exists.
                try:
                    (changeby["changedby822"], changeby["changedby2047"],
                     changeby["changedbyname"], changeby["changedbyemail"]) = \
                     utils.fix_maintainer (j["changed-by"])
                except ParseMaintError, msg:
                    (changeby["changedby822"], changeby["changedby2047"],
                     changeby["changedbyname"], changeby["changedbyemail"]) = \
                     ("", "", "", "")
                changedby="%s:%s" % (changeby["changedbyname"], changeby["changedbyemail"])

                distribution=j["distribution"].keys()
                closes=j["closes"].keys()
                fingerprint=j["fingerprint"]
                if j.has_key("sponsoremail"):
                    sponsor=j["sponsoremail"]
            for arch in j["architecture"].keys():
                arches[arch] = ""
            version = j["version"]
            versions[version] = ""
        arches_list = arches.keys()
        arches_list.sort(utils.arch_compare_sw)
        arch_list = " ".join(arches_list)
        version_list = " ".join(versions.keys())
        if len(version_list) > max_version_len:
            max_version_len = len(version_list)
        if len(arch_list) > max_arch_len:
            max_arch_len = len(arch_list)
        if i[1]["note_state"]:
            note = " | [N]"
        else:
            note = ""
        entries.append([source, version_list, arch_list, note, last_modified, maint, distribution, closes, fingerprint, sponsor, changedby])

    # direction entry consists of "Which field, which direction, time-consider" where
    # time-consider says how we should treat last_modified. Thats all.

    # Look for the options for sort and then do the sort.
    age = "h"
    if Cnf.has_key("Queue-Report::Options::Age"):
        age =  Cnf["Queue-Report::Options::Age"]
    if Cnf.has_key("Queue-Report::Options::New"):
    # If we produce html we always have oldest first.
        direction.append([4,-1,"ao"])
    else:
        if Cnf.has_key("Queue-Report::Options::Sort"):
            for i in Cnf["Queue-Report::Options::Sort"].split(","):
                if i == "ao":
                    # Age, oldest first.
                    direction.append([4,-1,age])
                elif i == "an":
                    # Age, newest first.
                    direction.append([4,1,age])
                elif i == "na":
                    # Name, Ascending.
                    direction.append([0,1,0])
                elif i == "nd":
                    # Name, Descending.
                    direction.append([0,-1,0])
                elif i == "nl":
                    # Notes last.
                    direction.append([3,1,0])
                elif i == "nf":
                    # Notes first.
                    direction.append([3,-1,0])
    entries.sort(lambda x, y: sortfunc(x, y))
    # Yes, in theory you can add several sort options at the commandline with. But my mind is to small
    # at the moment to come up with a real good sorting function that considers all the sidesteps you
    # have with it. (If you combine options it will simply take the last one at the moment).
    # Will be enhanced in the future.

    if Cnf.has_key("Queue-Report::Options::New"):
        direction.append([4,1,"ao"])
        entries.sort(lambda x, y: sortfunc(x, y))
    # Output for a html file. First table header. then table_footer.
    # Any line between them is then a <tr> printed from subroutine table_row.
        if len(entries) > 0:
            total_count = len(changes_files)
            source_count = len(per_source_items)
            table_header(type.upper(), source_count, total_count)
            for entry in entries:
                (source, version_list, arch_list, note, last_modified, maint, distribution, closes, fingerprint, sponsor, changedby) = entry
                table_row(source, version_list, arch_list, time_pp(last_modified), maint, distribution, closes, fingerprint, sponsor, changedby)
            table_footer(type.upper())
    else:
    # The "normal" output without any formatting.
        format="%%-%ds | %%-%ds | %%-%ds%%s | %%s old\n" % (max_source_len, max_version_len, max_arch_len)

        msg = ""
        for entry in entries:
            (source, version_list, arch_list, note, last_modified, undef, undef, undef, undef, undef, undef) = entry
            msg += format % (source, version_list, arch_list, note, time_pp(last_modified))

        if msg:
            total_count = len(changes_files)
            source_count = len(per_source_items)
            print type.upper()
            print "-"*len(type)
            print
            print msg
            print "%s %s source package%s / %s %s package%s in total." % (source_count, type, plural(source_count), total_count, type, plural(total_count))
            print


################################################################################

def main():
    global Cnf, Upload

    Cnf = utils.get_conf()
    Arguments = [('h',"help","Queue-Report::Options::Help"),
                 ('n',"new","Queue-Report::Options::New"),
                 ('s',"sort","Queue-Report::Options::Sort", "HasArg"),
                 ('a',"age","Queue-Report::Options::Age", "HasArg")]
    for i in [ "help" ]:
        if not Cnf.has_key("Queue-Report::Options::%s" % (i)):
            Cnf["Queue-Report::Options::%s" % (i)] = ""

    apt_pkg.ParseCommandLine(Cnf, Arguments, sys.argv)

    Options = Cnf.SubTree("Queue-Report::Options")
    if Options["Help"]:
        usage()

    Upload = queue.Upload(Cnf)

    if Cnf.has_key("Queue-Report::Options::New"):
        header()

    directories = Cnf.ValueList("Queue-Report::Directories")
    if not directories:
        directories = [ "byhand", "new" ]

    for directory in directories:
        changes_files = glob.glob("%s/*.changes" % (Cnf["Dir::Queue::%s" % (directory)]))
        process_changes_files(changes_files, directory)

    if Cnf.has_key("Queue-Report::Options::New"):
        footer()

################################################################################

if __name__ == '__main__':
    main()
