from django import forms
from .models import Valoracion, Team


class ValoracionForm(forms.ModelForm):
    class Meta:
        model = Valoracion
        fields = ['equipo', 'puntuacion', 'comentario']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Clase común para todos los inputs
        input_classes = 'w-full px-4 py-2 bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 transition'

        for field_name, field in self.fields.items():
            field.widget.attrs.update({'class': input_classes})

        # Ajustes específicos
        self.fields['puntuacion'].widget.attrs.update({'min': '1', 'max': '10', 'placeholder': 'Puntúa de 1 a 10'})
        self.fields['comentario'].widget.attrs.update({'rows': '3', 'placeholder': '¿Por qué esta nota?'})