def calculate_score(temp, humidity, soil, light):
    score = 100.0

    def stress(value, ideal, scale, power):
        return (abs(value - ideal) / scale) ** power

    score -= stress(temp,     72, 18, 1.4) * 22
    score -= stress(humidity, 45, 25, 1.2) * 18
    score -= stress(soil,     75, 20, 1.5) * 35
    score -= stress(light,    80, 30, 1.1) * 15

    if temp > 85 and soil < 30:  score -= 12
    if soil > 75 and humidity > 80: score -= 10
    if light < 20 and humidity > 70: score -= 8
    if temp < 45 or temp > 95:   score -= 10
    if humidity < 15 or humidity > 90: score -= 8
    if soil < 10:  score -= 12
    if light < 10: score -= 10

    return max(0, min(100, round(score)))
