from flask import Blueprint, request, jsonify, current_app
from flask_login import login_user, logout_user, login_required, current_user
from models import db, User
import jwt
from datetime import datetime, timedelta
import os

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    
    # Validate required fields
    required_fields = ['username', 'email', 'password', 'first_name', 'last_name', 'role']
    for field in required_fields:
        if field not in data:
            return jsonify({'message': f'Missing required field: {field}'}), 400
    
    # Check if user already exists
    if User.query.filter_by(username=data['username']).first():
        return jsonify({'message': 'Username already exists'}), 400
    
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'message': 'Email already exists'}), 400
    
    # Create new user
    new_user = User(
        username=data['username'],
        email=data['email'],
        first_name=data['first_name'],
        last_name=data['last_name'],
        role=data['role']
    )
    new_user.set_password(data['password'])
    
    # Save to database
    db.session.add(new_user)
    db.session.commit()
    
    # Login the user
    login_user(new_user)
    
    # Generate JWT token
    token = generate_token(new_user)
    
    return jsonify({
        'message': 'User registered successfully',
        'user': new_user.to_dict(),
        'token': token
    }), 201

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    
    # Validate login data
    if not data or not data.get('username') or not data.get('password'):
        return jsonify({'message': 'Username and password are required'}), 400
    
    # Find the user
    user = User.query.filter_by(username=data['username']).first()
    
    # Check if user exists and password is correct
    if not user or not user.check_password(data['password']):
        return jsonify({'message': 'Invalid credentials'}), 401
    
    # Check if user is active
    if not user.is_active:
        return jsonify({'message': 'Account is disabled'}), 403
    
    # Login the user
    login_user(user)
    
    # Generate JWT token
    token = generate_token(user)
    
    return jsonify({
        'message': 'Login successful',
        'user': user.to_dict(),
        'token': token
    }), 200

@auth_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return jsonify({'message': 'Logout successful'}), 200

@auth_bp.route('/user', methods=['GET'])
@login_required
def get_user():
    return jsonify({
        'user': current_user.to_dict()
    }), 200

@auth_bp.route('/update-theme', methods=['POST'])
@login_required
def update_theme():
    data = request.get_json()
    
    if 'theme' not in data or data['theme'] not in ['light', 'dark']:
        return jsonify({'message': 'Invalid theme preference'}), 400
    
    current_user.theme_preference = data['theme']
    db.session.commit()
    
    return jsonify({
        'message': 'Theme preference updated',
        'theme': current_user.theme_preference
    }), 200

# Helper function to generate JWT token
def generate_token(user):
    payload = {
        'user_id': user.id,
        'username': user.username,
        'exp': datetime.utcnow() + timedelta(days=1)
    }
    
    token = jwt.encode(
        payload,
        current_app.config.get('SECRET_KEY'),
        algorithm='HS256'
    )
    
    return token