"""
WTForms for News/Announcement forms.
"""
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField
from wtforms.validators import DataRequired, Length


class NewsForm(FlaskForm):
    """Form for creating/updating news announcements."""

    title = StringField('Judul', validators=[
        DataRequired(message='Judul harus diisi.'),
        Length(min=3, max=200, message='Judul harus 3-200 karakter.')
    ])

    category = SelectField('Kategori', choices=[
        ('News', 'News / Information'),
        ('Schedule', 'Activity Schedule')
    ], validators=[DataRequired(message='Kategori harus dipilih.')])

    content = TextAreaField('Isi Pengumuman', validators=[
        DataRequired(message='Isi pengumuman harus diisi.'),
        Length(min=10, message='Isi pengumuman minimal 10 karakter.')
    ])
