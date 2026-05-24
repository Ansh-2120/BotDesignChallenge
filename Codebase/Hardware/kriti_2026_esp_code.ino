// ================= IR SENSOR PINS =================

const int IR_far_left  = 22;    // old 21
const int IR_left      = 21;    // old 4
const int IR_middle    = 5;     //old 23
const int IR_right     = 23 ;   // old 5
const int IR_far_right = 4 ;    //old 22

const int IR_obj_detection = 19;

// ================= MOTOR PINS =================

#define AIN1 26 ///26 
#define AIN2 27   //27
#define PWMA 25

#define BIN1 14  //32 old
#define BIN2 32  //33 old
#define PWMB 33

#define STBY 12

// ================= US SENSOR PINS =================

// #define TRIG 18
// #define ECHO 19

const int pwmFreq = 1000;
const int pwmResolution = 8;

const int pwmChannelA = 0;
const int pwmChannelB = 1;


// ================= SPEED SETTINGS =================

int base_speed = 250;
int turn_speed = 200;
int strong_correction_speed = 170;


// ================= TURN TIMING =================

int left_turn_time  = 305;
int right_turn_time = 335;

// ================= OBJECT  TIMING =================

int object_forward_1_time = 750; //xtime
int object_forward_2_time = 600; //ytime
 // int object_forward_3_time = 265; // ztime

int object_left_turn_time = 530 ;
int object_right_turn_time = 370;


// ================= MOTOR FUNCTIONS =================

void forward()
{
  ledcWrite(PWMA, base_speed);
  ledcWrite(PWMB, base_speed);

  digitalWrite(AIN1, HIGH);
  digitalWrite(AIN2, LOW);

  digitalWrite(BIN1, HIGH);
  digitalWrite(BIN2, LOW);
}

void backward()
{
  ledcWrite(PWMA, base_speed);
  ledcWrite(PWMB, base_speed);

  digitalWrite(AIN1, LOW);
  digitalWrite(AIN2, HIGH);

  digitalWrite(BIN1, LOW);
  digitalWrite(BIN2, HIGH);
}

void slight_left()
{
  ledcWrite(PWMA, base_speed/4);
  ledcWrite(PWMB, base_speed);

  digitalWrite(AIN1, HIGH);
  digitalWrite(AIN2, LOW);

  digitalWrite(BIN1, HIGH);
  digitalWrite(BIN2, LOW);
}

void slight_right()
{
  ledcWrite(PWMA, base_speed);
  ledcWrite(PWMB, base_speed/4);

  digitalWrite(AIN1, HIGH);
  digitalWrite(AIN2, LOW);

  digitalWrite(BIN1, HIGH);
  digitalWrite(BIN2, LOW);
}


// ===== STRONG CORRECTIONS (NO PIVOT) =====

void strong_left()
{
  ledcWrite(PWMA, base_speed/3);
  ledcWrite(PWMB, strong_correction_speed);

  digitalWrite(AIN1, HIGH);
  digitalWrite(AIN2, LOW);

  digitalWrite(BIN1, HIGH);
  digitalWrite(BIN2, LOW);
}

void strong_right()
{
  ledcWrite(PWMA, strong_correction_speed);
  ledcWrite(PWMB, base_speed/3);

  digitalWrite(AIN1, HIGH);
  digitalWrite(AIN2, LOW);

  digitalWrite(BIN1, HIGH);
  digitalWrite(BIN2, LOW);
}


// ===== HARD INTERSECTION TURNS =====

void turn_left()
{
  ledcWrite(PWMA, turn_speed);
  ledcWrite(PWMB, turn_speed);

  digitalWrite(AIN1, LOW);
  digitalWrite(AIN2, HIGH);

  digitalWrite(BIN1, HIGH);
  digitalWrite(BIN2, LOW);
  
}

void turn_right()
{
  ledcWrite(PWMA, turn_speed);
  ledcWrite(PWMB, turn_speed);

  digitalWrite(AIN1, HIGH);
  digitalWrite(AIN2, LOW);

  digitalWrite(BIN1, LOW);
  digitalWrite(BIN2, HIGH);
  
}

void stop_bot()
{
  ledcWrite(PWMA, 0);
  ledcWrite(PWMB, 0);

  digitalWrite(AIN1, LOW);
  digitalWrite(AIN2, LOW);

  digitalWrite(BIN1, LOW);
  digitalWrite(BIN2, LOW);
}

// ===== OBJECT AVOIDANCE MOVES =====

void object_turn_left()
{
  turn_left();
  delay(object_left_turn_time);
}

void object_turn_right()
{
  turn_right();
  delay(object_right_turn_time);
}

void move_forward_1()
{
  forward();
  delay(object_forward_1_time);
}

void move_forward_2()
{
  forward();
  delay(object_forward_2_time);
}

void move_forward_3()
{
  while(!(digitalRead(IR_middle))){
    forward();
  }
  stop_bot();
  delay(50);
}

void perpendicular_turn_left(){
  turn_left();
  delay(100);
  while(!digitalRead(IR_middle)){
    turn_left();
  }
  stop_bot();
}

void perpendicular_turn_right(){
  turn_right();
  delay(100);
  while(!digitalRead(IR_middle)){
    turn_right();
  }
  stop_bot();
}


void object_avoidance(){

  backward();
  delay(500);

  stop_bot();
  delay(500);


     object_turn_left();
  //
   stop_bot();
   delay(1000);
  move_forward_1();
  stop_bot();
   delay(1000);
  object_turn_right();
  stop_bot();
   delay(1000);
  // move_forward_2();
  // stop_bot();
  //  delay(1000);
  // object_turn_right();
  //  stop_bot();
  //  delay(1000);
   move_forward_3();

}

// ================= SETUP =================

void setup()
{

  Serial.begin(115200);
  pinMode(IR_far_left, INPUT_PULLUP);
  pinMode(IR_left, INPUT_PULLUP);
  pinMode(IR_middle, INPUT_PULLUP);
  pinMode(IR_right, INPUT_PULLUP);
  pinMode(IR_far_right, INPUT_PULLUP);

  pinMode(IR_obj_detection, INPUT);

  // pinMode(TRIG, OUTPUT);
  // pinMode(ECHO, INPUT);

  pinMode(AIN1, OUTPUT);
  pinMode(AIN2, OUTPUT);
  pinMode(BIN1, OUTPUT);
  pinMode(BIN2, OUTPUT);
  pinMode(STBY, OUTPUT);

  digitalWrite(STBY, HIGH);

  ledcAttach(PWMA, pwmFreq, pwmResolution);
  ledcAttach(PWMB, pwmFreq, pwmResolution);

  delay(1000);

//   //change after testing 
//   delay(2500);
//    object_turn_left();
//   //
//    stop_bot();
//    delay(1000);
//   move_forward_1();
//   stop_bot();
//    delay(1000);
//   object_turn_right();
//   stop_bot();
//    delay(1000);
//   move_forward_2();
//   stop_bot();
//    delay(1000);
//   object_turn_right();
//    stop_bot();
//    delay(1000);
//  //  move_forward_3();

}



// // ================= Distance getting function =================

// float getDistance()
// {
//   digitalWrite(TRIG, LOW);
//   delayMicroseconds(2);

//   digitalWrite(TRIG, HIGH);
//   delayMicroseconds(10);
//   digitalWrite(TRIG, LOW);

//   long duration = pulseIn(ECHO, HIGH);

//   float distance = duration * 0.0343 / 2;

//   return distance;
// }




// ================= MAIN LOOP =================

void loop()
{

  int FL = !digitalRead(IR_far_left);
  int L  = !digitalRead(IR_left);
  int M  = !digitalRead(IR_middle);
  int R  = !digitalRead(IR_right);
  int FR = !digitalRead(IR_far_right);

  int OJ = digitalRead(IR_obj_detection);


  Serial.print("FL: ");
  Serial.print(FL);
  Serial.print("  L: ");
  Serial.print(L);
  Serial.print("  M: ");
  Serial.print(M);
  Serial.print("  R: ");
  Serial.print(R);
  Serial.print("  FR: ");
  Serial.println(FR);

 // ================= OBJECT DETECTION PRIORITY =================
    // float distance = getDistance();

  // if(distance <= 2.75)
  // {
  //   object_turn_left();

  //   move_forward_1();

  //   object_turn_right();

  //   move_forward_2();

  //   object_turn_right();

  //   move_forward_3();

  //   object_turn_left();

  //   delay(100);

  //   return;
  // }

  // ================= INTERSECTION PRIORITY =================

  if(!OJ){
    object_avoidance();
    
    return;
  }

  // ================= INTERSECTION PRIORITY =================

  if (FL == LOW)  
  {
    perpendicular_turn_left();
    // delay(left_turn_time);
    return;
  }

  if (FR == LOW) 
  {
    perpendicular_turn_right();
    // delay(right_turn_time);
    return;
  }


  // ================= NORMAL LINE FOLLOW =================

  if (L == HIGH && M == LOW && R == HIGH)  
  {
    forward();
  }

  else if (L == LOW && M == HIGH && R == HIGH)
  {
    slight_left();
  }

  else if (L == HIGH && M == HIGH && R == LOW)
  {
    slight_right();
  }

  else if (L == LOW && M == LOW && R == HIGH)
  {
    strong_left();
  }

  else if (L == HIGH && M == LOW && R == LOW)
  {
    strong_right();
  }

  else if (L == LOW && M == LOW && R == LOW)
  {
    forward();
  }

  else if (L == HIGH && M == HIGH && R == HIGH)
  {
    stop_bot();
  }

  delay(20);
}