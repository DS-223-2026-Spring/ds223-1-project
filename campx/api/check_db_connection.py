"""Backend-local script for checking database connectivity and read helpers."""

from __future__ import annotations

from psycopg2 import OperationalError

try:
    from .SQLHandler import SQLHandler
    from .config import get_database_settings, load_backend_env
    from .crud import (
        get_ds_artifact,
        get_metrics_snapshot,
        get_model_state_snapshot,
        get_simulation_record,
        list_ds_artifacts,
        list_simulations,
    )
    from .db_interactions import (
        get_all_customers,
        get_customer_by_id,
        get_customer_latents,
        get_model_state,
        get_pending_interactions,
    )
except ImportError:
    from SQLHandler import SQLHandler
    from config import get_database_settings, load_backend_env
    from crud import (
        get_ds_artifact,
        get_metrics_snapshot,
        get_model_state_snapshot,
        get_simulation_record,
        list_ds_artifacts,
        list_simulations,
    )
    from db_interactions import (
        get_all_customers,
        get_customer_by_id,
        get_customer_latents,
        get_model_state,
        get_pending_interactions,
    )


REQUIRED_TABLES = (
    "customers",
    "customer_latents",
    "actions",
    "simulations",
    "interactions",
    "model_state",
)

OPTIONAL_TABLES = (
    "simulation_artifacts",
)


def _table_names(db) -> set[str]:
    tables = db.select(
        """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
        """
    )["table_name"].tolist()
    return set(tables)


def _exercise_read_helpers(db) -> list[str]:
    messages: list[str] = []

    customers = get_all_customers(db)
    customer_count = len(customers.index)
    messages.append(f"get_all_customers -> {customer_count} rows")

    if customer_count:
        sample_customer_id = int(customers.iloc[0]["customer_id"])
        customer = get_customer_by_id(db, sample_customer_id)
        latents = get_customer_latents(db, sample_customer_id)
        messages.append(
            "get_customer_by_id -> "
            f"{'ok' if customer is not None else 'missing'} for customer_id={sample_customer_id}"
        )
        messages.append(
            "get_customer_latents -> "
            f"{'found' if latents is not None else 'none'} for customer_id={sample_customer_id}"
        )
    else:
        messages.append("get_customer_by_id/get_customer_latents skipped -> no customers found")

    pending = get_pending_interactions(db, older_than_hours=0)
    messages.append(f"get_pending_interactions -> {len(pending.index)} rows")

    state_pair = db.select(
        """
        SELECT simulation_id, action_id
        FROM public.model_state
        ORDER BY simulation_id, action_id
        LIMIT 1
        """
    )
    if state_pair.empty:
        messages.append("get_model_state skipped -> no model_state rows")
    else:
        simulation_id = int(state_pair.iloc[0]["simulation_id"])
        action_id = int(state_pair.iloc[0]["action_id"])
        model_state = get_model_state(db, simulation_id, action_id)
        messages.append(
            "get_model_state -> "
            f"{'ok' if model_state is not None else 'missing'} "
            f"for simulation_id={simulation_id}, action_id={action_id}"
        )

    return messages


def _exercise_backend_snapshots(db) -> list[str]:
    messages: list[str] = []
    tables = _table_names(db)

    simulations = list_simulations(db)
    messages.append(f"list_simulations -> {len(simulations)} rows")
    if not simulations:
        messages.append("Simulation-dependent CRUD checks skipped -> no simulations found")
        return messages

    simulation_id = int(simulations[0]["simulation_id"])
    simulation = get_simulation_record(db, simulation_id)
    messages.append(
        "get_simulation_record -> "
        f"{'ok' if simulation is not None else 'missing'} for simulation_id={simulation_id}"
    )

    metrics = get_metrics_snapshot(db, simulation_id)
    messages.append(
        "get_metrics_snapshot -> "
        f"{'ok' if metrics is not None else 'missing'} for simulation_id={simulation_id}"
    )

    model_state = get_model_state_snapshot(db, simulation_id)
    messages.append(
        "get_model_state_snapshot -> "
        f"{'ok' if model_state is not None else 'missing'} for simulation_id={simulation_id}"
    )

    if "simulation_artifacts" not in tables:
        messages.append(
            "DS artifact checks skipped -> simulation_artifacts table is missing "
            "(re-apply DB migrations or recreate the volume to enable DS artifact storage)"
        )
        return messages

    artifacts = list_ds_artifacts(db, simulation_id)
    artifact_count = len(artifacts) if artifacts is not None else 0
    messages.append(
        f"list_ds_artifacts -> {artifact_count} rows for simulation_id={simulation_id}"
    )
    if artifacts:
        first_artifact_name = str(artifacts[0]["artifact_name"])
        artifact = get_ds_artifact(db, simulation_id, first_artifact_name)
        messages.append(
            "get_ds_artifact -> "
            f"{'ok' if artifact is not None else 'missing'} "
            f"for simulation_id={simulation_id}, artifact_name={first_artifact_name}"
        )
    else:
        messages.append("get_ds_artifact skipped -> no simulation_artifacts rows found")

    return messages


def main() -> int:
    load_backend_env()
    settings = get_database_settings()
    db = None

    try:
        db = SQLHandler(**settings)

        summary = db.select(
            """
            SELECT
                current_database() AS db_name,
                current_user AS db_user
            """
        ).iloc[0]

        tables = _table_names(db)
        missing_tables = [table for table in REQUIRED_TABLES if table not in tables]
        missing_optional_tables = [
            table for table in OPTIONAL_TABLES if table not in tables
        ]

        print("Database connection OK")
        print(f"Host: {settings['host']}:{settings['port']}")
        print(f"Database: {summary['db_name']}")
        print(f"User: {summary['db_user']}")

        if missing_tables:
            print("Missing required tables:")
            for table in missing_tables:
                print(f"- {table}")
            return 1

        print("Required tables present:")
        for table in REQUIRED_TABLES:
            print(f"- {table}")
        if missing_optional_tables:
            print("Optional integration tables missing:")
            for table in missing_optional_tables:
                print(f"- {table}")

        print("Shared read helpers:")
        for message in _exercise_read_helpers(db):
            print(f"- {message}")

        print("Backend CRUD integration:")
        for message in _exercise_backend_snapshots(db):
            print(f"- {message}")
        return 0

    except OperationalError as exc:
        print("Database connection failed")
        print(
            "Tried: "
            f"host={settings['host']} "
            f"port={settings['port']} "
            f"dbname={settings['dbname']} "
            f"user={settings['user']}"
        )
        print("Tip: override DB_HOST/DB_PORT/DB_NAME/DB_USER/DB_PASSWORD or POSTGRES_* vars if needed.")
        print(str(exc))
        return 1
    except Exception as exc:
        print("Database verification failed")
        print(
            "Tried: "
            f"host={settings['host']} "
            f"port={settings['port']} "
            f"dbname={settings['dbname']} "
            f"user={settings['user']}"
        )
        print(str(exc))
        return 1

    finally:
        if db is not None:
            db.close()


if __name__ == "__main__":
    raise SystemExit(main())
