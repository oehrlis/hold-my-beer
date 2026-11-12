import click

from .extensions import db
from .pool import DEFAULT_POOL_FILE


def register_cli(app):
    @app.cli.command("seed-data")
    @click.option("--pool", "pool_file", default=None, envvar="POOL_FILE",
                  help="Pool-Datei (YAML). Standard: POOL_FILE bzw. %s ab App-Verzeichnis" % DEFAULT_POOL_FILE)
    def seed_command(pool_file):
        """Legt Runden, Themen und Reserve-Themen aus der Pool-Datei an (idempotent, loescht keine Stimmen)."""
        from .pool import PoolError
        from .services.seed import seed_data
        try:
            rep = seed_data(pool_file or app.config["POOL_FILE"])
        except PoolError as e:
            raise click.ClickException(str(e))
        for w in rep["warnings"]:
            click.echo("WARNUNG: " + w, err=True)
        click.echo("Seed-Daten geladen aus %s: %d Runden, %d Optionen, %d Reserve-Themen%s." % (
            rep["path"], rep["rounds"], rep["options"], rep["reserve"],
            ", %d Warnung(en)" % len(rep["warnings"]) if rep["warnings"] else ""))

    @app.cli.command("backup")
    @click.option("--dest", default=None, help="Zielverzeichnis (Standard: BACKUP_DIR)")
    def backup_command(dest):
        """Konsistentes SQLite-Backup ueber die Online-Backup-API."""
        from .services.backup import backup_database
        click.echo(str(backup_database(dest)))

    @app.cli.command("export-json")
    @click.option("--out", default=None, help="Ausgabedatei (Standard: stdout)")
    def export_command(out):
        """Exportiert Runden, Themen, Stimmen, Ergebnisse und Scorecards als JSON."""
        from .services.backup import export_json
        text = export_json(out)
        click.echo(out if out else text)
