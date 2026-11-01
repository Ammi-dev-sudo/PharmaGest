from django.db import models
from django.templatetags.static import static

FORME_IMAGE_MAP = {
    'COMPRIME': 'comprime',
    'GELULE': 'gelule',
    'SIROP': 'sirop',
    'POMMADE': 'pommade',
    'CREME': 'creme',
    'INJECTION': 'injection',
    'SOLUTION': 'solution',
    'AUTRE': 'autre',
}


class Categorie(models.Model):
    nom = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Catégorie'
        verbose_name_plural = 'Catégories'
        ordering = ['nom']

    def __str__(self):
        return self.nom


class Medicament(models.Model):
    FORME_CHOICES = (
        ('COMPRIME', 'Comprimé'),
        ('GELULE', 'Gélule'),
        ('SIROP', 'Sirop'),
        ('POMMADE', 'Pommade'),
        ('CREME', 'Crème'),
        ('INJECTION', 'Injection'),
        ('SOLUTION', 'Solution'),
        ('AUTRE', 'Autre'),
    )
    STATUT_CHOICES = (
        ('ACTIF', 'Actif'),
        ('ARCHIVE', 'Archivé'),
    )

    nom_commercial = models.CharField(max_length=200)
    denomination_generique = models.CharField(max_length=200, blank=True)
    categorie = models.ForeignKey(Categorie, on_delete=models.PROTECT, related_name='medicaments')
    forme_pharmaceutique = models.CharField(max_length=20, choices=FORME_CHOICES)
    dosage = models.CharField(max_length=100)
    laboratoire = models.CharField(max_length=150, blank=True)
    code_barres = models.CharField(max_length=100, unique=True, blank=True, null=True)
    photo = models.ImageField(upload_to='medicaments/', blank=True, null=True)
    prix_achat = models.DecimalField(max_digits=10, decimal_places=2)
    prix_vente = models.DecimalField(max_digits=10, decimal_places=2)
    seuil_alerte = models.IntegerField(default=10)
    statut = models.CharField(max_length=10, choices=STATUT_CHOICES, default='ACTIF')
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Médicament'
        verbose_name_plural = 'Médicaments'
        ordering = ['nom_commercial']

    def __str__(self):
        return f"{self.nom_commercial} - {self.dosage}"

    def stock_total(self):
        from stock.models import LotStock
        total = LotStock.objects.filter(medicament=self, quantite__gt=0).aggregate(total=models.Sum('quantite'))
        return total['total'] or 0

    @property
    def image_url(self):
        """Photo uploadée ou photo réelle de la forme galénique de secours."""
        if self.photo:
            try:
                return self.photo.url
            except ValueError:
                pass
        key = FORME_IMAGE_MAP.get(self.forme_pharmaceutique, 'autre')
        return static(f'images/medicaments/reels/{key}.jpg')

    @property
    def est_epuise(self):
        return self.stock_total() <= 0

    @property
    def est_en_alerte(self):
        return 0 < self.stock_total() <= self.seuil_alerte

    @property
    def marge_unitaire(self):
        return self.prix_vente - self.prix_achat
