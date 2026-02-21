from django import forms
from .models import Valoracion, Team


class ValoracionForm(forms.ModelForm):
    class Meta:
        model = Valoracion
        fields = ['equipo', 'puntuacion', 'comentario']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        input_classes = 'w-full px-4 py-2 bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 transition'

        for field_name, field in self.fields.items():
            field.widget.attrs.update({'class': input_classes})

        self.fields['puntuacion'].widget.attrs.update({'min': '1', 'max': '10', 'placeholder': 'Puntúa de 1 a 10'})
        self.fields['comentario'].widget.attrs.update({'rows': '3', 'placeholder': '¿Por qué esta nota?'})

from django import forms
from .models import Categoria, Team

class CategoriaForm(forms.ModelForm):
    equipos = forms.MultipleChoiceField(
        choices=[],
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Equipos de la categoría"
    )

    class Meta:
        model = Categoria
        fields = ['nombre', 'temporada', 'imagen', 'equipos']
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 focus:ring-4 focus:ring-blue-500/10 outline-none transition-all',
                'placeholder': 'Ej: Juvenil Masculino'
            }),
            'temporada': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 focus:ring-4 focus:ring-blue-500/10 outline-none transition-all',
                'placeholder': 'Ej: 2024/25'
            }),
            'imagen': forms.FileInput(attrs={
                'class': 'block w-full text-sm text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100 cursor-pointer border border-slate-200 rounded-xl p-2'
            }),
        }

    def __init__(self, *args, **kwargs):
        super(CategoriaForm, self).__init__(*args, **kwargs)
        self.fields['equipos'].choices = [
            (str(equipo.pk), equipo.nombre)
            for equipo in Team.objects.using('mongo_db').all().order_by('nombre')
        ]

class CSVImportForm(forms.Form):
    archivo_csv = forms.FileField(
        label="Seleccionar archivo CSV",
        widget=forms.FileInput(attrs={'class': 'block w-full text-sm text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100 cursor-pointer'})
    )