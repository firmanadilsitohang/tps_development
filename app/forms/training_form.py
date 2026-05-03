"""
WTForms for Training Schedule forms.
"""
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, IntegerField, DateTimeField
from wtforms.validators import DataRequired, Length, NumberRange, Optional


class TrainingForm(FlaskForm):
    """Form for creating/updating training schedules."""

    title = StringField('Judul Training', validators=[
        DataRequired(message='Judul training harus diisi.'),
        Length(min=3, max=150, message='Judul harus 3-150 karakter.')
    ])

    training_date = DateTimeField('Tanggal & Waktu', validators=[
        DataRequired(message='Tanggal & waktu harus diisi.')
    ], format='%Y-%m-%dT%H:%M')

    location = StringField('Lokasi', validators=[
        DataRequired(message='Lokasi harus diisi.'),
        Length(min=3, max=100, message='Lokasi harus 3-100 karakter.')
    ])

    quota = IntegerField('Kuota', validators=[
        Optional(),
        NumberRange(min=0, max=1000, message='Kuota harus antara 0-1000.')
    ])

    description = TextAreaField('Deskripsi', validators=[
        Optional(),
        Length(max=500, message='Deskripsi maksimal 500 karakter.')
    ])
