class MongoRouter:
    """
    Un router para controlar que las tablas de la app 'rankingWaterpolo'
    vayan a MongoDB, y todo lo demás (usuarios, admin) se quede en SQLite.
    """

    # Nombre de tu app donde están los modelos de equipos, partidos, etc.
    route_app_labels = {'rankingWaterpolo'}

    def db_for_read(self, model, **hints):
        if model._meta.app_label in self.route_app_labels:
            return 'mongo_db'  # Tus datos de waterpolo a Mongo
        return 'default'  # Los usuarios a SQLite

    def db_for_write(self, model, **hints):
        if model._meta.app_label in self.route_app_labels:
            return 'mongo_db'
        return 'default'

    def allow_relation(self, obj1, obj2, **hints):
        # Permite relaciones si ambos están en la misma DB
        if (
                obj1._meta.app_label in self.route_app_labels or
                obj2._meta.app_label in self.route_app_labels
        ):
            return True
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if app_label in self.route_app_labels:
            return db == 'mongo_db'  # Migrar tu app solo en Mongo
        return db == 'default'  # Migrar usuarios solo en SQLite