# -*- coding: utf-8 -*-

"""Simple script to dump all records in an Invenio instance to JSON."""

import json

import click


@click.group()
def cmd():
    """Command for dumping all records as JSON."""
    pass


@cmd.command()
def dumprecords():
    """Dump records."""
    from invenio.base.factory import create_app

    app = create_app()
    with app.app_context():
        from invenio.modules.editor.models import Bibrec
        from invenio.modules.records.api import Record
        data = []
        q = Bibrec.query
        with click.progressbar(q, length=q.count()) as query:
            for r in query:
                d = Record.get_record(r.id)
                if d:
                    data.append(d.dumps(clean=True))

        with open('dump2.json', 'w') as f:
            json.dump(data, f)


@cmd.command()
def dumpfiles():
    """Dump files."""
    from invenio.base.factory import create_app

    app = create_app()
    with app.app_context():
        from invenio.modules.editor.models import Bibdoc
        from invenio.legacy.bibdocfile.api import BibDoc

        q = Bibdoc.query
        with open('files.json', 'w') as fp:
            fp.write("[")
            with click.progressbar(q, length=q.count()) as query:
                for d in query:
                    bd = BibDoc(d.id)
                    try:
                        for f in bd.docfiles:
                            fp.write(json.dumps(dict(
                                comment=f.comment,
                                creation_date=f.cd.isoformat(),
                                modification_date=f.md.isoformat(),
                                description=f.description,
                                docid=f.docid,
                                encoding=f.encoding,
                                flags=f.flags,
                                format=f.get_format(),
                                hidden=f.hidden,
                                is_icon=f.is_icon(),
                                magic=f.get_magic(),
                                md5=f.get_checksum(),
                                mime=f.mime,
                                name=f.get_full_name(),
                                path=f.fullpath,
                                recid=f.get_recid(),
                                size=f.size,
                                status=f.status,
                                subformat=f.get_subformat(),
                                version=f.version,
                            )))
                            fp.write(",")
                    except Exception:
                        print "Failed: %s" % bd.id
            fp.seek(fp.tell()-1)
            fp.write("]")


if __name__ == "__main__":
    cmd()
