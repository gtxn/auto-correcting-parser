import sqlalchemy as db
from sqlalchemy.orm import sessionmaker

# Database connection details
SOURCE_DB_URL = 'mysql+pymysql://user:password@source_host/source_db'
DEST_DB_URL = 'mysql+pymysql://user:password@dest_host/dest_db'

# Create engine for source and destination databases
source_engine = db.create_engine(SOURCE_DB_URL)
dest_engine = db.create_engine(DEST_DB_URL)

# Create session for both databases
SourceSession = sessionmaker(bind=source_engine)
DestSession = sessionmaker(bind=dest_engine)

def migrate_data(source_table, dest_table):
    source_session = SourceSession()
    dest_session = DestSession()
    
    try:
        # Fetch data from source table
        data = source_session.execute(f'SELECT * FROM {source_table}').fetchall()

        # Insert data into destination table
        for row in data:
            dest_session.execute(
                dest_table.insert().values(**dict(row))
            )
        
        dest_session.commit()
        print(f"Data migrated from {source_table} to {dest_table}")

    except Exception as e:
        dest_session.rollback()
        print(f"Error during migration: {e}")

    finally:
        source_session.close()
        dest_session.close()

if __name__ == '__main__':
    # Define your source and destination tables here
    source_table_name = 'source_table'
    dest_table_name = db.Table('dest_table', db.MetaData(), autoload_with=dest_engine)

    migrate_data(source_table_name, dest_table_name)
