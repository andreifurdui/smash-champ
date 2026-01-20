"""Match score submission forms."""
from flask_wtf import FlaskForm
from wtforms import IntegerField, SubmitField
from wtforms.validators import DataRequired, NumberRange, ValidationError, Optional


class ScoreSubmissionForm(FlaskForm):
    """Form for submitting match scores."""

    # Set 1 (required)
    set1_player1 = IntegerField('Set 1 - Your Score', validators=[
        DataRequired(),
        NumberRange(min=0, max=30, message='Score must be 0-30')
    ])
    set1_player2 = IntegerField('Set 1 - Opponent Score', validators=[
        DataRequired(),
        NumberRange(min=0, max=30, message='Score must be 0-30')
    ])

    # Set 2 (required)
    set2_player1 = IntegerField('Set 2 - Your Score', validators=[
        DataRequired(),
        NumberRange(min=0, max=30, message='Score must be 0-30')
    ])
    set2_player2 = IntegerField('Set 2 - Opponent Score', validators=[
        DataRequired(),
        NumberRange(min=0, max=30, message='Score must be 0-30')
    ])

    # Set 3 (optional unless tied)
    set3_player1 = IntegerField('Set 3 - Your Score', validators=[
        Optional(),
        NumberRange(min=0, max=30, message='Score must be 0-30')
    ])
    set3_player2 = IntegerField('Set 3 - Opponent Score', validators=[
        Optional(),
        NumberRange(min=0, max=30, message='Score must be 0-30')
    ])

    submit = SubmitField('Submit Score')

    def _is_valid_set(self, score1, score2):
        """Validate table tennis rules: First to 11, win by 2."""
        if score1 is None or score2 is None:
            return False
        high = max(score1, score2)
        low = min(score1, score2)
        # Must reach 11 and win by at least 2
        return high >= 11 and (high - low) >= 2

    def validate_set1_player1(self, field):
        """Validate Set 1 is complete and valid."""
        if not self._is_valid_set(field.data, self.set1_player2.data):
            raise ValidationError('Set 1 invalid: Must reach 11 and win by 2')

    def validate_set2_player1(self, field):
        """Validate Set 2 is complete and valid."""
        if not self._is_valid_set(field.data, self.set2_player2.data):
            raise ValidationError('Set 2 invalid: Must reach 11 and win by 2')

    def validate_set3_player1(self, field):
        """Validate Set 3 if provided."""
        # Set 3 is optional unless match is tied
        if field.data is not None and self.set3_player2.data is not None:
            if not self._is_valid_set(field.data, self.set3_player2.data):
                raise ValidationError('Set 3 invalid: Must reach 11 and win by 2')

    def validate(self, extra_validators=None):
        """Custom validation for match result."""
        if not super().validate(extra_validators):
            return False

        # Count sets won by each player
        p1_sets = 0
        p2_sets = 0

        # Set 1
        if self.set1_player1.data > self.set1_player2.data:
            p1_sets += 1
        else:
            p2_sets += 1

        # Set 2
        if self.set2_player1.data > self.set2_player2.data:
            p1_sets += 1
        else:
            p2_sets += 1

        # Set 3 (if provided)
        if self.set3_player1.data is not None and self.set3_player2.data is not None:
            if self.set3_player1.data > self.set3_player2.data:
                p1_sets += 1
            else:
                p2_sets += 1

        # Validate match result
        if p1_sets == p2_sets:
            # Tied - need Set 3
            if self.set3_player1.data is None or self.set3_player2.data is None:
                self.set3_player1.errors.append('Set 3 required when tied 1-1')
                return False

        # One player must have won 2 sets
        if p1_sets < 2 and p2_sets < 2:
            self.set1_player1.errors.append('Match incomplete: No player won 2 sets')
            return False

        return True
