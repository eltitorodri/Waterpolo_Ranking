class MongoRouter:
    """
    Un router para controlar que las tablas de la app 'rankingWaterpolo'
    vayan a MongoDB, y todo lo demás (usuarios, admin) se quede en SQLite.
    """

    route_app_labels = {'rankingWaterpolo'}

    def db_for_read(self, model, **hints):
        if model._meta.app_label in self.route_app_labels:
            return 'mongo_db'
        return 'default'

    def db_for_write(self, model, **hints):
        if model._meta.app_label in self.route_app_labels:
            return 'mongo_db'
        return 'default'

    def allow_relation(self, obj1, obj2, **hints):
        # Solo permite relaciones si ambos objetos están en la misma base de datos
        if (
            obj1._meta.app_label in self.route_app_labels and
            obj2._meta.app_label in self.route_app_labels
        ):
            return True
        elif (
            obj1._meta.app_label not in self.route_app_labels and
            obj2._meta.app_label not in self.route_app_labels
        ):
            return True
        return False # Bloquea relaciones cruzadas (ej: ForeignKey de Mongo a SQLite)

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if app_label in self.route_app_labels:
            return db == 'mongo_db'
        return db == 'default'