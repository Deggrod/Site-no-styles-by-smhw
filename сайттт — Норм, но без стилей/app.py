from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import os
import numpy as np
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(os.path.abspath(os.path.dirname(__file__)), 'university.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    fullname = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    programming_score = db.Column(db.Integer)
    math_analysis_score = db.Column(db.Integer)
    aig_score = db.Column(db.Integer)
    has_debts = db.Column(db.Boolean, default=False)
    gpa = db.Column(db.Float)
    interests = db.Column(db.String(50))
    goals = db.Column(db.String(50))
    python_skill = db.Column(db.Boolean, default=False)
    java_skill = db.Column(db.Boolean, default=False)
    javascript_skill = db.Column(db.Boolean, default=False)
    last_ahp_update = db.Column(db.DateTime)

    def calculate_gpa(self):
        self.gpa = round((self.programming_score + self.math_analysis_score + self.aig_score) / 3, 2)

class Track(db.Model):
    __tablename__ = 'tracks'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    required_programming = db.Column(db.Integer)
    required_math = db.Column(db.Integer)
    required_aig = db.Column(db.Integer)
    accepts_with_debts = db.Column(db.Boolean, default=False)
    description = db.Column(db.Text)
    interest_match = db.Column(db.Float)
    career_utility = db.Column(db.Float)
    difficulty = db.Column(db.Float)
    practical_work = db.Column(db.Float)
    research_opportunity = db.Column(db.Float)

class AHPMatrix(db.Model):
    __tablename__ = 'ahp_matrices'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    criteria = db.Column(db.String(500))
    matrix_data = db.Column(db.Text)
    weights = db.Column(db.Text)
    consistency_ratio = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

def initialize_database():
    with app.app_context():
        db.create_all()
        if not Track.query.first():
            tracks = [
                Track(
                    name="Инженерный трек",
                    required_programming=4,
                    required_math=3,
                    required_aig=2,
                    accepts_with_debts=False,
                    description="Для будущих технических лидеров и архитекторов",
                    interest_match=0.7,
                    career_utility=0.9,
                    difficulty=0.8,
                    practical_work=0.6,
                    research_opportunity=0.7
                ),
                Track(
                    name="Программно-аппаратный трек",
                    required_programming=3,
                    required_math=4,
                    required_aig=3,
                    accepts_with_debts=True,
                    description="Для разработчиков системного ПО и embedded-решений",
                    interest_match=0.6,
                    career_utility=0.8,
                    difficulty=0.7,
                    practical_work=0.8,
                    research_opportunity=0.5
                ),
                Track(
                    name="Трек тестирования",
                    required_programming=4,
                    required_math=2,
                    required_aig=2,
                    accepts_with_debts=True,
                    description="Для специалистов по обеспечению качества ПО",
                    interest_match=0.5,
                    career_utility=0.7,
                    difficulty=0.5,
                    practical_work=0.9,
                    research_opportunity=0.3
                )
            ]
            db.session.add_all(tracks)
            db.session.commit()

initialize_database()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            if User.query.filter_by(username=request.form['username']).first():
                flash('Логин уже занят', 'danger')
                return redirect(url_for('register'))
            
            new_user = User(
                fullname=request.form['fullname'],
                username=request.form['username'],
                password=generate_password_hash(request.form['password']),
                programming_score=int(request.form['programming_score']),
                math_analysis_score=int(request.form['math_analysis_score']),
                aig_score=int(request.form['aig_score']),
                has_debts='has_debts' in request.form,
                interests=request.form['interests'],
                goals=request.form['goals'],
                python_skill='python_skill' in request.form,
                java_skill='java_skill' in request.form,
                javascript_skill='javascript_skill' in request.form
            )
            new_user.calculate_gpa()
            
            db.session.add(new_user)
            db.session.commit()
            
            login_user(new_user)
            flash('Регистрация успешна', 'success')
            return redirect(url_for('profile'))
        except ValueError:
            flash('Оценки должны быть числами 1-5', 'danger')
        except Exception as e:
            flash(f'Ошибка: {str(e)}', 'danger')
            db.session.rollback()
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and check_password_hash(user.password, request.form['password']):
            login_user(user)
            return redirect(url_for('profile'))
        flash('Неверный логин/пароль', 'danger')
    return render_template('login.html')

@app.route('/profile')
@login_required
def profile():
    user = current_user
    if user.gpa is None:
        user.calculate_gpa()
        db.session.commit()
    
    tracks = Track.query.all()
    recommendations = []
    for track in tracks:
        if (user.programming_score >= track.required_programming and
            user.math_analysis_score >= track.required_math and
            user.aig_score >= track.required_aig and
            (not user.has_debts or track.accepts_with_debts)):
            recommendations.append(track)
    
    return render_template('profile.html',
                         user=user,
                         recommendations=recommendations)

@app.route('/update_scores', methods=['POST'])
@login_required
def update_scores():
    user = current_user
    try:
        user.programming_score = int(request.form['programming_score'])
        user.math_analysis_score = int(request.form['math_analysis_score'])
        user.aig_score = int(request.form['aig_score'])
        user.has_debts = 'has_debts' in request.form
        user.calculate_gpa()
        db.session.commit()
        flash('Оценки успешно обновлены', 'success')
    except ValueError:
        flash('Оценки должны быть числами 1-5', 'danger')
    except Exception as e:
        flash(f'Ошибка: {str(e)}', 'danger')
        db.session.rollback()
    return redirect(url_for('profile'))

@app.route('/update_password', methods=['POST'])
@login_required
def update_password():
    user = current_user
    if not check_password_hash(user.password, request.form['current_password']):
        flash('Текущий пароль неверен', 'danger')
    elif request.form['new_password'] != request.form['confirm_password']:
        flash('Новые пароли не совпадают', 'danger')
    else:
        try:
            user.password = generate_password_hash(request.form['new_password'])
            db.session.commit()
            flash('Пароль успешно изменен', 'success')
        except Exception as e:
            flash(f'Ошибка: {str(e)}', 'danger')
            db.session.rollback()
    return redirect(url_for('profile'))

@app.route('/ahp')
@login_required
def ahp():
    return render_template('ahp.html')

@app.route('/api/ahp/calculate', methods=['POST'])
@login_required
def calculate_ahp():
    try:
        data = request.get_json()
        matrix = np.array(data['matrix'])
        criteria = data['criteria']
        
        # Calculate weights
        geometric_means = np.prod(matrix, axis=1) ** (1.0 / len(matrix))
        weights = (geometric_means / geometric_means.sum()).tolist()
        
        # Calculate consistency
        n = len(matrix)
        weighted_sum = np.dot(matrix, weights)
        lambda_max = np.sum(weighted_sum / weights) / n
        ci = (lambda_max - n) / (n - 1)
        ri = {1:0, 2:0, 3:0.58, 4:0.9, 5:1.12, 6:1.24, 7:1.32, 8:1.41, 9:1.45, 10:1.49}.get(n, 1.5)
        cr = ci / ri
        
        # Save to database
        matrix_record = AHPMatrix(
            user_id=current_user.id,
            criteria=','.join(criteria),
            matrix_data=str(matrix.tolist()),
            weights=str(weights),
            consistency_ratio=cr
        )
        db.session.add(matrix_record)
        current_user.last_ahp_update = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'weights': weights,
            'consistency_ratio': cr,
            'is_consistent': cr <= 0.1
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 400

@app.route('/api/tracks/suggest', methods=['POST'])
@login_required
def suggest_tracks():
    try:
        data = request.get_json()
        weights = data['weights']
        criteria = data['criteria']
        
        tracks = Track.query.all()
        suggestions = []
        
        for track in tracks:
            score = 0
            if 'Соответствие интересам' in criteria:
                idx = criteria.index('Соответствие интересам')
                score += weights[idx] * track.interest_match
            if 'Полезность для карьеры' in criteria:
                idx = criteria.index('Полезность для карьеры')
                score += weights[idx] * track.career_utility
            if 'Уровень сложности' in criteria:
                idx = criteria.index('Уровень сложности')
                score += weights[idx] * (1 - track.difficulty)  # Inverse for difficulty
            if 'Практические занятия' in criteria:
                idx = criteria.index('Практические занятия')
                score += weights[idx] * track.practical_work
            if 'Исследовательские проекты' in criteria:
                idx = criteria.index('Исследовательские проекты')
                score += weights[idx] * track.research_opportunity
            
            suggestions.append({
                'id': track.id,
                'name': track.name,
                'description': track.description,
                'score': round(score, 4),
                'match_percentage': round(score * 100, 1)
            })
        
        suggestions.sort(key=lambda x: x['score'], reverse=True)
        
        return jsonify({
            'status': 'success',
            'suggestions': suggestions
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 400

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)