from django.db import models
from django.contrib.auth.models import User

import os
import wave
import numpy as np
from aubio import source, tempo

# Create your models here.

class Tag(models.Model):
    name = models.CharField(max_length=100)


class Sample(models.Model):
    # Audio Sample

    class Key(models.TextChoices):
        # Key Enum
        A = 'A'
        B = 'B'
        C = 'C'
        D = 'D'
        E = 'E'
        F = 'F'
        G = 'G'

    class Mode(models.TextChoices):
        # Mode Enum
        MINOR = 'min'
        MAJOR = 'maj'

    def user_directory_path(instance, filename):
        # File will be uploaded to MEDIA_ROOT/samples/<username>/<sample_name>
        ext = os.path.splitext(filename)[1]
        return 'samples/{0}/{1}{2}'.format(instance.user.username, instance.name, ext)

    # Table columns
    user = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    name = models.CharField(max_length=255)
    file = models.FileField(max_length=255, upload_to=user_directory_path)
    duration = models.DecimalField(max_digits=4, decimal_places=1, blank=True, null=True) # duration in [s]
    tempo = models.PositiveIntegerField(blank=True, null=True) # tempo is > 0
    key = models.CharField(max_length=1, choices=Key.choices, blank=True)
    mode = models.CharField(max_length=3, choices=Mode.choices, blank=True)
    description = models.TextField(blank=True, default='No description provided.')
    datetime_upload = models.DateTimeField(auto_now_add=True) # auto now at creation
    nb_dl_unauthenticated = models.PositiveIntegerField(default=0) # nb dl > 0
    tags = models.ManyToManyField(Tag) # a sample can have multiple tags

    def deduce_properties(self):
        frames = 0
        rate = 0
        with wave.open(self.file, 'rb') as f:
            frames = f.getnframes()
            rate = f.getframerate()
        
        self._deduce_duration(frames, rate)
        self._deduce_tempo(rate)

    def _deduce_duration(self, frames, rate):
        self.duration = frames / float(rate)

    def _deduce_tempo(self, rate):
        win_s, hop_s = 1024, 512
        s = source(self.file.path, rate, hop_s)
        o = tempo('specdiff', win_s, hop_s, rate)
        # List of beats, in samples
        beats = []

        while True:
            samples, read = s()
            is_beat = o(samples)
            if is_beat:
                this_beat = o.get_last_s()
                beats.append(this_beat)
            if read < hop_s:
                break

        if len(beats) > 1:
            self.tempo = np.mean(60. / np.diff(beats))
        else:
            self.tempo = 0
            

class UserProfile(models.Model):
    
    def user_directory_path(instance, filename):
        ext = os.path.splitext(filename)[1]
        return 'users/{0}/pp{1}'.format(instance.user.id, ext)

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    description = models.TextField(blank=True, default='No description provided.')
    profile_picture = models.FileField(max_length=255, upload_to=user_directory_path, blank=True, default='default/pictures/pp.png')
    email_public = models.BooleanField(default=False)


class UserSampleDownload(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    sample = models.ForeignKey(Sample, on_delete=models.CASCADE)
    datetime_download = models.DateTimeField(auto_now_add=True) # auto now at creation


class SampleForkFrom(models.Model):
    sample = models.ForeignKey(Sample, related_name='sample_fork_from_base', on_delete=models.CASCADE)
    sample_from = models.ForeignKey(Sample, related_name='sample_fork_from', on_delete=models.CASCADE)


class SampleForkTo(models.Model):
    sample = models.ForeignKey(Sample, related_name='sample_fork_to_base', on_delete=models.CASCADE)
    sample_to = models.ForeignKey(Sample, related_name='sample_fork_to', on_delete=models.CASCADE)
