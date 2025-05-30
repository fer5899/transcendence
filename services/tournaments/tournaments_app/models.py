from django.db import models

class Tournament(models.Model):
    name = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    tournament_tree = models.JSONField(default=dict)
    champion = models.ForeignKey('Participant', on_delete=models.SET_NULL, null=True, blank=True, related_name='won_tournaments')
    participants = models.ManyToManyField('Participant', through='TournamentParticipant', blank=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.name

class Participant(models.Model):
    user_id = models.IntegerField(unique=False)
    username = models.CharField(max_length=100)

    def __str__(self):
        return self.username

class TournamentParticipant(models.Model):
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE)
    participant = models.ForeignKey(Participant, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('tournament', 'participant')

    def __str__(self):
        return f"{self.participant.username} en {self.tournament.name}"
