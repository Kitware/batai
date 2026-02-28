from __future__ import annotations

from django.contrib.gis.db import models

sample_frame_map = {
    12: "Mexico",
    14: "Contintental US",
    19: "Canada",
    20: "Alaska",
    21: "Puerto Rico",
    15: "Hawaii",
    22: "Offshore Caribbean",
    23: "Offshore AKCAN",
    24: "Offshore CONUS",
    25: "Offshore Hawaii",
    26: "Offshore Mexico",
}


class GRTSCells(models.Model):
    id = models.IntegerField(primary_key=True)
    grts_cell_id = models.IntegerField()
    sample_frame_id = models.IntegerField(blank=True, null=True)
    grts_geom = models.GeometryField(blank=True, null=True)
    # continue defining all fields similarly
    geom_4326 = models.GeometryField()

    @property
    def sample_frame_mapping(self):
        return sample_frame_map[self.sample_frame_id]

    @staticmethod
    def sort_order():
        return [14, 20, 15, 24, 21, 19, 12, 22, 23, 25, 26]
