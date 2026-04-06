from django.db import models

class AttackLog(models.Model):
    # id alanı Django tarafından otomatik tanınır, tekrar yazmaya gerek yok
    timestamp = models.DateTimeField()
    ip_address = models.CharField(max_length=45)
    port = models.IntegerField()
    module = models.CharField(max_length=50)
    username = models.CharField(max_length=100, null=True, blank=True)
    password = models.CharField(max_length=255, null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    session_id = models.CharField(max_length=8)
    event_data = models.TextField(null=True, blank=True)
    response_data = models.TextField(null=True, blank=True)
    country_code = models.CharField(max_length=2, default="??")

    class Meta:
        managed = False # Django bu tabloyu modifiye etmesin
        db_table = 'attack_logs' # Veritabanındaki gerçek tablo adı

    def __str__(self):
        return f"{self.timestamp} - {self.ip_address} - {self.module}"