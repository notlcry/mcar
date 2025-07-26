#!/usr/bin/python3
"""
情感响应准确性自动化测试
测试情感检测算法的准确性和一致性
"""

import time
import logging
import json
import statistics
from typing import Dict, List, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime

from emotion_engine import EmotionEngine, EmotionType, EmotionalState

# 设置日志
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class EmotionTestCase:
    """情感测试用例"""
    text: str
    expected_emotion: EmotionType
    expected_intensity_range: Tuple[float, float]
    category: str  # 'positive', 'negative', 'neutral', 'complex'
    description: str

@dataclass
class EmotionTestResult:
    """情感测试结果"""
    test_case: EmotionTestCase
    detected_emotion: EmotionType
    detected_intensity: float
    is_emotion_correct: bool
    is_intensity_in_range: bool
    confidence_score: float
    processing_time: float
    timestamp: datetime

class EmotionAccuracyTester:
    """情感准确性测试器"""
    
    def __init__(self):
        self.emotion_engine = EmotionEngine()
        self.test_cases = self._load_test_cases()
        self.results: List[EmotionTestResult] = []
    
    def _load_test_cases(self) -> List[EmotionTestCase]:
        """加载测试用例"""
        return [
            # 积极情感测试
            EmotionTestCase(
                text="太棒了！我今天心情特别好！",
                expected_emotion=EmotionType.HAPPY,
                expected_intensity_range=(0.7, 1.0),
                category="positive",
                description="强烈积极情感"
            ),
            EmotionTestCase(
                text="哇，这真是太令人兴奋了！",
                expected_emotion=EmotionType.EXCITED,
                expected_intensity_range=(0.8, 1.0),
                category="positive",
                description="兴奋情感"
            ),
            EmotionTestCase(
                text="我很开心能和你聊天。",
                expected_emotion=EmotionType.HAPPY,
                expected_intensity_range=(0.5, 0.8),
                category="positive",
                description="中等积极情感"
            ),
            
            # 消极情感测试
            EmotionTestCase(
                text="我今天很难过，什么都不想做。",
                expected_emotion=EmotionType.SAD,
                expected_intensity_range=(0.6, 0.9),
                category="negative",
                description="悲伤情感"
            ),
            EmotionTestCase(
                text="这让我感到很困惑，不知道该怎么办。",
                expected_emotion=EmotionType.CONFUSED,
                expected_intensity_range=(0.5, 0.8),
                category="negative",
                description="困惑情感"
            ),
            EmotionTestCase(
                text="我有点担心这个问题。",
                expected_emotion=EmotionType.SAD,
                expected_intensity_range=(0.3, 0.6),
                category="negative",
                description="轻微担忧"
            ),
            
            # 中性情感测试
            EmotionTestCase(
                text="今天天气不错。",
                expected_emotion=EmotionType.NEUTRAL,
                expected_intensity_range=(0.2, 0.5),
                category="neutral",
                description="中性陈述"
            ),
            EmotionTestCase(
                text="我需要思考一下这个问题。",
                expected_emotion=EmotionType.THINKING,
                expected_intensity_range=(0.4, 0.7),
                category="neutral",
                description="思考状态"
            ),
            
            # 复杂情感测试
            EmotionTestCase(
                text="虽然有点担心，但我还是很期待明天的活动。",
                expected_emotion=EmotionType.EXCITED,  # 主导情感
                expected_intensity_range=(0.4, 0.7),
                category="complex",
                description="混合情感"
            ),
            EmotionTestCase(
                text="我不确定这是对还是错，让我想想。",
                expected_emotion=EmotionType.CONFUSED,
                expected_intensity_range=(0.5, 0.8),
                category="complex",
                description="不确定性"
            ),
            
            # 动作相关情感测试
            EmotionTestCase(
                text="我们一起跳舞吧！",
                expected_emotion=EmotionType.EXCITED,
                expected_intensity_range=(0.7, 1.0),
                category="action",
                description="动作邀请"
            ),
            EmotionTestCase(
                text="让我转个圈给你看！",
                expected_emotion=EmotionType.HAPPY,
                expected_intensity_range=(0.6, 0.9),
                category="action",
                description="展示动作"
            ),
            
            # 社交情感测试
            EmotionTestCase(
                text="谢谢你陪我聊天，我很感激。",
                expected_emotion=EmotionType.HAPPY,
                expected_intensity_range=(0.5, 0.8),
                category="social",
                description="感激情感"
            ),
            EmotionTestCase(
                text="我想和你做朋友。",
                expected_emotion=EmotionType.HAPPY,
                expected_intensity_range=(0.6, 0.9),
                category="social",
                description="友好情感"
            ),
            
            # 边界情况测试
            EmotionTestCase(
                text="",
                expected_emotion=EmotionType.NEUTRAL,
                expected_intensity_range=(0.0, 0.3),
                category="edge_case",
                description="空文本"
            ),
            EmotionTestCase(
                text="？？？",
                expected_emotion=EmotionType.CONFUSED,
                expected_intensity_range=(0.3, 0.7),
                category="edge_case",
                description="疑问符号"
            )
        ]
    
    def run_single_test(self, test_case: EmotionTestCase) -> EmotionTestResult:
        """运行单个情感测试"""
        start_time = time.time()
        
        try:
            # 分析情感
            emotional_state = self.emotion_engine.analyze_response_emotion(test_case.text)
            
            processing_time = time.time() - start_time
            
            # 检查结果
            is_emotion_correct = emotional_state.emotion_type == test_case.expected_emotion
            is_intensity_in_range = (
                test_case.expected_intensity_range[0] <= emotional_state.intensity <= 
                test_case.expected_intensity_range[1]
            )
            
            # 计算置信度分数
            confidence_score = self._calculate_confidence_score(
                emotional_state, test_case, is_emotion_correct, is_intensity_in_range
            )
            
            result = EmotionTestResult(
                test_case=test_case,
                detected_emotion=emotional_state.emotion_type,
                detected_intensity=emotional_state.intensity,
                is_emotion_correct=is_emotion_correct,
                is_intensity_in_range=is_intensity_in_range,
                confidence_score=confidence_score,
                processing_time=processing_time,
                timestamp=datetime.now()
            )
            
            return result
            
        except Exception as e:
            logger.error(f"情感测试失败: {e}")
            return EmotionTestResult(
                test_case=test_case,
                detected_emotion=EmotionType.NEUTRAL,
                detected_intensity=0.0,
                is_emotion_correct=False,
                is_intensity_in_range=False,
                confidence_score=0.0,
                processing_time=time.time() - start_time,
                timestamp=datetime.now()
            )
    
    def _calculate_confidence_score(self, emotional_state: EmotionalState, 
                                  test_case: EmotionTestCase, 
                                  emotion_correct: bool, 
                                  intensity_correct: bool) -> float:
        """计算置信度分数"""
        score = 0.0
        
        # 情感类型正确性 (60%权重)
        if emotion_correct:
            score += 0.6
        
        # 强度准确性 (30%权重)
        if intensity_correct:
            score += 0.3
        else:
            # 部分分数基于强度接近程度
            expected_mid = sum(test_case.expected_intensity_range) / 2
            intensity_diff = abs(emotional_state.intensity - expected_mid)
            intensity_score = max(0, 1 - intensity_diff) * 0.3
            score += intensity_score
        
        # 处理时间奖励 (10%权重)
        if emotional_state.processing_time < 0.1:  # 假设有处理时间属性
            score += 0.1
        elif emotional_state.processing_time < 0.5:
            score += 0.05
        
        return min(1.0, score)
    
    def run_all_tests(self) -> Dict:
        """运行所有情感准确性测试"""
        print("开始情感响应准确性测试")
        print("=" * 50)
        
        self.results.clear()
        
        for i, test_case in enumerate(self.test_cases, 1):
            print(f"测试 {i}/{len(self.test_cases)}: {test_case.description}")
            
            result = self.run_single_test(test_case)
            self.results.append(result)
            
            # 显示结果
            status = "✓" if result.is_emotion_correct and result.is_intensity_in_range else "✗"
            print(f"  {status} 期望: {test_case.expected_emotion.value} | "
                  f"检测: {result.detected_emotion.value} | "
                  f"强度: {result.detected_intensity:.2f} | "
                  f"置信度: {result.confidence_score:.2f}")
        
        # 生成统计报告
        return self._generate_accuracy_report()
    
    def _generate_accuracy_report(self) -> Dict:
        """生成准确性报告"""
        if not self.results:
            return {}
        
        # 基本统计
        total_tests = len(self.results)
        emotion_correct = sum(1 for r in self.results if r.is_emotion_correct)
        intensity_correct = sum(1 for r in self.results if r.is_intensity_in_range)
        both_correct = sum(1 for r in self.results if r.is_emotion_correct and r.is_intensity_in_range)
        
        # 按类别统计
        category_stats = {}
        for result in self.results:
            category = result.test_case.category
            if category not in category_stats:
                category_stats[category] = {
                    'total': 0,
                    'emotion_correct': 0,
                    'intensity_correct': 0,
                    'both_correct': 0
                }
            
            category_stats[category]['total'] += 1
            if result.is_emotion_correct:
                category_stats[category]['emotion_correct'] += 1
            if result.is_intensity_in_range:
                category_stats[category]['intensity_correct'] += 1
            if result.is_emotion_correct and result.is_intensity_in_range:
                category_stats[category]['both_correct'] += 1
        
        # 计算准确率
        for category in category_stats:
            stats = category_stats[category]
            stats['emotion_accuracy'] = stats['emotion_correct'] / stats['total']
            stats['intensity_accuracy'] = stats['intensity_correct'] / stats['total']
            stats['overall_accuracy'] = stats['both_correct'] / stats['total']
        
        # 置信度统计
        confidence_scores = [r.confidence_score for r in self.results]
        processing_times = [r.processing_time for r in self.results]
        
        # 混淆矩阵
        confusion_matrix = self._calculate_confusion_matrix()
        
        report = {
            'summary': {
                'total_tests': total_tests,
                'emotion_accuracy': emotion_correct / total_tests,
                'intensity_accuracy': intensity_correct / total_tests,
                'overall_accuracy': both_correct / total_tests,
                'average_confidence': statistics.mean(confidence_scores),
                'average_processing_time': statistics.mean(processing_times)
            },
            'category_breakdown': category_stats,
            'confidence_distribution': {
                'min': min(confidence_scores),
                'max': max(confidence_scores),
                'median': statistics.median(confidence_scores),
                'std_dev': statistics.stdev(confidence_scores) if len(confidence_scores) > 1 else 0
            },
            'performance_metrics': {
                'min_processing_time': min(processing_times),
                'max_processing_time': max(processing_times),
                'median_processing_time': statistics.median(processing_times)
            },
            'confusion_matrix': confusion_matrix,
            'detailed_results': [asdict(r) for r in self.results],
            'timestamp': datetime.now().isoformat()
        }
        
        return report
    
    def _calculate_confusion_matrix(self) -> Dict:
        """计算混淆矩阵"""
        emotions = list(EmotionType)
        matrix = {emotion.value: {e.value: 0 for e in emotions} for emotion in emotions}
        
        for result in self.results:
            expected = result.test_case.expected_emotion.value
            detected = result.detected_emotion.value
            matrix[expected][detected] += 1
        
        return matrix
    
    def save_report(self, report: Dict, filename: str = None):
        """保存测试报告"""
        if filename is None:
            filename = f"emotion_accuracy_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2, default=str)
        
        print(f"\n情感准确性报告已保存到: {filename}")
        return filename
    
    def print_summary(self, report: Dict):
        """打印测试摘要"""
        summary = report['summary']
        
        print("\n" + "=" * 50)
        print("情感响应准确性测试摘要")
        print("=" * 50)
        print(f"总测试数: {summary['total_tests']}")
        print(f"情感类型准确率: {summary['emotion_accuracy']:.1%}")
        print(f"强度准确率: {summary['intensity_accuracy']:.1%}")
        print(f"整体准确率: {summary['overall_accuracy']:.1%}")
        print(f"平均置信度: {summary['average_confidence']:.3f}")
        print(f"平均处理时间: {summary['average_processing_time']:.3f}秒")
        
        print("\n按类别统计:")
        for category, stats in report['category_breakdown'].items():
            print(f"  {category}:")
            print(f"    情感准确率: {stats['emotion_accuracy']:.1%}")
            print(f"    强度准确率: {stats['intensity_accuracy']:.1%}")
            print(f"    整体准确率: {stats['overall_accuracy']:.1%}")
        
        # 显示表现最差的测试用例
        worst_results = sorted(self.results, key=lambda r: r.confidence_score)[:3]
        if worst_results:
            print("\n需要改进的测试用例:")
            for i, result in enumerate(worst_results, 1):
                print(f"  {i}. {result.test_case.description}")
                print(f"     文本: '{result.test_case.text}'")
                print(f"     期望: {result.test_case.expected_emotion.value}")
                print(f"     检测: {result.detected_emotion.value}")
                print(f"     置信度: {result.confidence_score:.3f}")

def main():
    """主函数"""
    try:
        # 创建测试器
        tester = EmotionAccuracyTester()
        
        # 运行测试
        report = tester.run_all_tests()
        
        # 显示摘要
        tester.print_summary(report)
        
        # 保存报告
        tester.save_report(report)
        
        # 检查是否达到最低准确率要求
        min_accuracy_threshold = 0.7  # 70%
        if report['summary']['overall_accuracy'] >= min_accuracy_threshold:
            print(f"\n✅ 情感检测准确率达标 ({report['summary']['overall_accuracy']:.1%} >= {min_accuracy_threshold:.1%})")
            return 0
        else:
            print(f"\n⚠️  情感检测准确率未达标 ({report['summary']['overall_accuracy']:.1%} < {min_accuracy_threshold:.1%})")
            return 1
    
    except KeyboardInterrupt:
        print("\n测试被用户中断")
        return 1
    except Exception as e:
        print(f"\n❌ 情感准确性测试失败: {e}")
        return 1

if __name__ == "__main__":
    exit(main())