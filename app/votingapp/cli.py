import click

from .extensions import db


def register_cli(app):
    @app.cli.command("seed-data")
    def seed_command():
        """Legt Runden, Themen und Reserve-Themen an (idempotent, loescht keine Stimmen)."""
        from .services.seed import seed_data
        seed_data()
        click.echo("Seed-Daten geladen.")

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
