# SmartLimo AI - Configuration Alembic (migrations de base de données)
#
# Ce fichier est le script d'environnement standard généré par
# `alembic init` : il définit COMMENT Alembic se connecte à la base et
# exécute les migrations, mais ne contient aucune migration lui-même
# (celles-ci se trouvent dans alembic/versions/). Il n'est pas destiné à
# être modifié au quotidien, sauf pour brancher `target_metadata` sur les
# modèles de l'application (voir commentaire plus bas) afin de permettre
# la génération automatique de migrations (`alembic revision --autogenerate`).

import os
from logging.config import fileConfig

from dotenv import load_dotenv
from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
# Objet de configuration Alembic : donne accès aux valeurs définies dans
# alembic.ini (dont l'URL de connexion à la base, sqlalchemy.url).
config = context.config

# alembic.ini est un fichier INI (configparser), pas du Python : l'URL de
# connexion ne peut donc pas y être calculée depuis une variable
# d'environnement. On la charge ici à la place et on l'injecte dans la
# config Alembic en mémoire.
load_dotenv()
config.set_main_option("sqlalchemy.url", os.getenv("DATABASE_URL"))

# Interpret the config file for Python logging.
# This line sets up loggers basically.
# Configure le logging Python à partir des sections définies dans
# alembic.ini, pour que les messages d'Alembic (SQL exécuté, etc.)
# s'affichent correctement pendant une migration.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# Importer app.models (même si l'import semble inutilisé) est indispensable :
# c'est ce qui enregistre chaque classe de modèle sur Base.metadata avant
# qu'Alembic ne compare ce metadata au schéma réel de la base. Sans cet
# import, target_metadata = Base.metadata serait vide et
# `alembic revision --autogenerate` générerait une migration vide.
from app.database import Base
from app import models  # noqa: F401

target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    # Mode "offline" : Alembic ne se connecte pas réellement à la base,
    # il génère seulement les instructions SQL correspondant aux
    # migrations (utile pour les revoir avant exécution, ou les exécuter
    # manuellement sur un autre environnement).
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    # Mode "online" (le mode utilisé en pratique par `alembic upgrade`) :
    # une vraie connexion à la base est ouverte et les migrations sont
    # exécutées directement dessus.
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,  # pas de pool de connexions : une seule connexion, le temps de la migration
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


# Point d'entrée du script : choisit le mode online ou offline selon la
# façon dont Alembic a été invoqué (option --sql en ligne de commande
# active le mode offline).
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
