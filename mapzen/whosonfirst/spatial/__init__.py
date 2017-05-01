class base:

    def __init__(self, **kwargs):
        pass

    def point_in_polygon(self, lat, lon, placetype, **kwargs):
        raise Exception, "Method 'point_in_polygon' not implemented by this class."

    def intersects(self, feature, **kwargs):
        raise Exception, "Method 'intersects' not implemented by this class."

    def intersects_paginated(self, feature, **kwargs):
        raise Exception, "Method 'intersects_paginated' not implemented by this class."

    def row_to_feature(self, row, **kwargs):
        raise Exception, "Method 'row_to_feature' not implemented by this class."
